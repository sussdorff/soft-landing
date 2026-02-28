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
      // No list endpoint — return what we know about.
      // If empty, fetch the default simulation disruption.
      if (knownDisruptions.size === 0) {
        try {
          const d = await fetchJSON<Disruption>("/disruptions/dis-snowstorm-001");
          knownDisruptions.set(d.id, d);
        } catch {
          // not found — that's fine
        }
      }
      return Array.from(knownDisruptions.values());
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
      // Backend has per-passenger options, not per-disruption.
      // Fetch passenger list, then batch-fetch options for each.
      const passengers = await fetchJSON<BackendPassenger[]>(
        `/disruptions/${disruptionId}/passengers`
      );

      const results: Record<string, Option[]> = {};

      // Fetch in parallel, batched to avoid overwhelming the server
      const BATCH_SIZE = 10;
      for (let i = 0; i < passengers.length; i += BATCH_SIZE) {
        const batch = passengers.slice(i, i + BATCH_SIZE);
        const optionsBatch = await Promise.all(
          batch.map((p) =>
            fetchJSON<Option[]>(`/passengers/${p.id}/options`).catch(() => [])
          )
        );
        batch.forEach((p, idx) => {
          results[p.id] = optionsBatch[idx];
        });
      }

      return results;
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
      // 1. Submit wish on behalf of passenger
      const wish = await fetchJSON<Wish>(`/passengers/${passengerId}/wish`, {
        method: "POST",
        body: JSON.stringify({
          disruptionId,
          selectedOptionId: optionId,
          rankedOptionIds: [optionId],
        }),
      });
      // 2. Immediately approve it
      await fetchJSON(`/wishes/${wish.id}/approve`, { method: "POST" });
      return { ...wish, status: "approved" as const };
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
