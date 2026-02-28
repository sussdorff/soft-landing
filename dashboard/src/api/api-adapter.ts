import type {
  DashboardAPI,
  Disruption,
  Passenger,
  Option,
  Wish,
  PassengerProfile,
  WSEvent,
  Segment,
} from "../types";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "https://softlanding.sussdorff.de";
const WS_URL =
  import.meta.env.VITE_WS_URL ||
  "wss://softlanding.sussdorff.de";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ── Backend response shapes (differ from dashboard types) ──────────

interface BackendPassenger {
  id: string;
  name: string;
  bookingRef: string;
  originalItinerary: Segment[]; // flat array, not { segments: [...] }
  status: string;
  denialCount: number;
  priority: number;
}

interface BackendProfile {
  passenger: BackendPassenger;
  options: Option[];
  wishes: Wish[];
  disruptions?: Disruption[];
}

// ── Transform helpers ──────────────────────────────────────────────

function adaptPassenger(raw: BackendPassenger): Passenger {
  return {
    ...raw,
    originalItinerary: { segments: raw.originalItinerary },
    status: raw.status as Passenger["status"],
  };
}

// ── Adapter ────────────────────────────────────────────────────────

export function createApiAdapter(): DashboardAPI {
  const eventHandlers: Set<(event: WSEvent) => void> = new Set();
  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let currentDisruptionId: string | null = null;

  // Track known disruptions so getDisruptions() can return them
  const knownDisruptions = new Map<string, Disruption>();

  function connectWS(disruptionId: string) {
    // Reconnect if switching disruptions
    if (currentDisruptionId !== disruptionId) {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      ws = null;
      currentDisruptionId = disruptionId;
    }
    if (ws) return;
    ws = new WebSocket(`${WS_URL}/ws/dashboard/${disruptionId}`);

    ws.onmessage = (msg) => {
      try {
        const event: WSEvent = JSON.parse(msg.data);
        eventHandlers.forEach((h) => h(event));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      ws = null;
      reconnectTimer = setTimeout(() => connectWS(disruptionId), 3000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  return {
    async getDisruptions() {
      const disruptions = await fetchJSON<Disruption[]>("/disruptions");
      for (const d of disruptions) {
        knownDisruptions.set(d.id, d);
      }
      return disruptions;
    },

    async getDisruption(id) {
      connectWS(id);
      const d = await fetchJSON<Disruption>(`/disruptions/${id}`);
      knownDisruptions.set(d.id, d);
      return d;
    },

    async getPassengers(disruptionId) {
      const raw = await fetchJSON<BackendPassenger[]>(
        `/disruptions/${disruptionId}/passengers`
      );
      return raw.map(adaptPassenger);
    },

    async getOptions(disruptionId) {
      return fetchJSON<Record<string, Option[]>>(
        `/disruptions/${disruptionId}/options`
      );
    },

    async getWishes(disruptionId) {
      return fetchJSON<Wish[]>(`/wishes?disruption_id=${disruptionId}`);
    },

    async getPassengerProfile(passengerId) {
      const raw = await fetchJSON<BackendProfile>(
        `/passengers/${passengerId}/profile`
      );
      const passenger = adaptPassenger(raw.passenger);
      return {
        ...passenger,
        options: raw.options,
        wishes: raw.wishes,
        disruptions: raw.disruptions,
      } as PassengerProfile;
    },

    async approveWish(wishId) {
      await fetchJSON(`/wishes/${wishId}/approve`, { method: "POST" });
    },

    async denyWish(wishId, reason) {
      await fetchJSON(`/wishes/${wishId}/deny`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    },

    async resolveManually(passengerId, optionId, disruptionId) {
      return fetchJSON<Wish>(`/passengers/${passengerId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ disruptionId, selectedOptionId: optionId }),
      });
    },

    onEvent(handler) {
      eventHandlers.add(handler);
      return () => {
        eventHandlers.delete(handler);
        if (eventHandlers.size === 0) {
          if (reconnectTimer) clearTimeout(reconnectTimer);
          ws?.close();
          ws = null;
        }
      };
    },
  };
}
