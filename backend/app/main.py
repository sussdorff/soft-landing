"""ReRoute — FastAPI backend for airline disruption management."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import store
from app.models import DenyRequest, SimulateRequest, Wish, WishRequest, WishStatus
from app.ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.seed_munich_snowstorm()
    yield


app = FastAPI(
    title="ReRoute API",
    description="Passenger disruption management for Lufthansa hackathon",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Disruptions ---

@app.post("/disruptions/simulate")
async def simulate_disruption(req: SimulateRequest):
    store.reset()
    dis_id = store.seed_munich_snowstorm()
    dis = store.disruptions[dis_id]
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions/{disruption_id}")
async def get_disruption(disruption_id: str):
    dis = store.disruptions.get(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    return dis.model_dump(by_alias=True, mode="json")


@app.get("/disruptions/{disruption_id}/passengers")
async def get_disruption_passengers(disruption_id: str):
    dis = store.disruptions.get(disruption_id)
    if not dis:
        raise HTTPException(404, "Disruption not found")
    pax_list = [
        store.passengers[pid]
        for pid in dis.affected_passenger_ids
        if pid in store.passengers
    ]
    pax_list.sort(key=lambda p: (-p.priority, p.name))
    return [p.model_dump(by_alias=True, mode="json") for p in pax_list]


# --- Passengers ---

@app.get("/passengers/{passenger_id}/disruptions")
async def get_passenger_disruptions(passenger_id: str):
    if passenger_id not in store.passengers:
        raise HTTPException(404, "Passenger not found")
    active = [
        d for d in store.disruptions.values()
        if passenger_id in d.affected_passenger_ids
    ]
    return [d.model_dump(by_alias=True, mode="json") for d in active]


@app.get("/passengers/{passenger_id}/options")
async def get_passenger_options(passenger_id: str):
    if passenger_id not in store.passengers:
        raise HTTPException(404, "Passenger not found")
    opts = store.options.get(passenger_id, [])
    return [o.model_dump(by_alias=True, mode="json") for o in opts]


@app.get("/passengers/{passenger_id}/status")
async def get_passenger_status(passenger_id: str):
    pax = store.passengers.get(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    return {
        "passengerId": pax.id,
        "name": pax.name,
        "status": pax.status,
        "denialCount": pax.denial_count,
        "priority": pax.priority,
    }


@app.get("/passengers/{passenger_id}/profile")
async def get_passenger_profile(passenger_id: str):
    pax = store.passengers.get(passenger_id)
    if not pax:
        raise HTTPException(404, "Passenger not found")
    pax_wishes = [w for w in store.wishes.values() if w.passenger_id == passenger_id]
    pax_disruptions = [
        d for d in store.disruptions.values()
        if passenger_id in d.affected_passenger_ids
    ]
    return {
        "passenger": pax.model_dump(by_alias=True, mode="json"),
        "options": [o.model_dump(by_alias=True, mode="json") for o in store.options.get(passenger_id, [])],
        "wishes": [w.model_dump(by_alias=True, mode="json") for w in pax_wishes],
        "disruptions": [d.model_dump(by_alias=True, mode="json") for d in pax_disruptions],
    }


@app.post("/passengers/{passenger_id}/wish")
async def submit_wish(passenger_id: str, req: WishRequest):
    if passenger_id not in store.passengers:
        raise HTTPException(404, "Passenger not found")
    pax = store.passengers[passenger_id]

    wish = Wish(
        passenger_id=passenger_id,
        disruption_id=req.disruption_id,
        selected_option_id=req.selected_option_id,
        ranked_option_ids=req.ranked_option_ids,
        submitted_at=datetime.now(tz=UTC),
    )
    store.wishes[wish.id] = wish
    pax.status = "chose"

    await manager.send_to_dashboard(req.disruption_id, "wish_submitted", {
        "wishId": wish.id,
        "passengerId": passenger_id,
        "selectedOptionId": req.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


# --- Wishes ---

@app.get("/wishes")
async def list_wishes(disruption_id: str = Query(None)):
    result = store.wishes.values()
    if disruption_id:
        result = [w for w in result if w.disruption_id == disruption_id]
    return [w.model_dump(by_alias=True, mode="json") for w in result]


@app.post("/wishes/{wish_id}/approve")
async def approve_wish(wish_id: str):
    wish = store.wishes.get(wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")
    wish.status = WishStatus.APPROVED
    wish.confirmation_details = "Approved by gate agent"

    pax = store.passengers.get(wish.passenger_id)
    if pax:
        pax.status = "approved"

    await manager.send_to_passenger(wish.passenger_id, "wish_approved", {
        "wishId": wish.id,
        "selectedOptionId": wish.selected_option_id,
    })
    return wish.model_dump(by_alias=True, mode="json")


@app.post("/wishes/{wish_id}/deny")
async def deny_wish(wish_id: str, req: DenyRequest):
    wish = store.wishes.get(wish_id)
    if not wish:
        raise HTTPException(404, "Wish not found")
    wish.status = WishStatus.DENIED
    wish.denial_reason = req.reason

    pax = store.passengers.get(wish.passenger_id)
    if pax:
        pax.status = "denied"
        pax.denial_count += 1

    await manager.send_to_passenger(wish.passenger_id, "wish_denied", {
        "wishId": wish.id,
        "reason": req.reason,
    })
    return wish.model_dump(by_alias=True, mode="json")


# --- WebSocket ---

@app.websocket("/ws/passenger/{passenger_id}")
async def ws_passenger(ws: WebSocket, passenger_id: str):
    await manager.connect_passenger(passenger_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text('{"type":"ack","data":{}}')
    except WebSocketDisconnect:
        manager.disconnect_passenger(passenger_id, ws)


@app.websocket("/ws/dashboard/{disruption_id}")
async def ws_dashboard(ws: WebSocket, disruption_id: str):
    await manager.connect_dashboard(disruption_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text('{"type":"ack","data":{}}')
    except WebSocketDisconnect:
        manager.disconnect_dashboard(disruption_id, ws)
