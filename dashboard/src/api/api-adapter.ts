import type { DashboardAPI, WSEvent } from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8001";

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

export function createApiAdapter(): DashboardAPI {
  const eventHandlers: Set<(event: WSEvent) => void> = new Set();
  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function connectWS(disruptionId: string) {
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
      // Auto-reconnect after 3s
      reconnectTimer = setTimeout(() => connectWS(disruptionId), 3000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  return {
    async getDisruptions() {
      return fetchJSON(`/disruptions`);
    },

    async getDisruption(id) {
      // Also establish WS connection when we first load a disruption
      connectWS(id);
      return fetchJSON(`/disruptions/${id}`);
    },

    async getPassengers(disruptionId) {
      return fetchJSON(`/disruptions/${disruptionId}/passengers`);
    },

    async getOptions(disruptionId) {
      return fetchJSON(`/disruptions/${disruptionId}/options`);
    },

    async getWishes(disruptionId) {
      return fetchJSON(`/wishes?disruption_id=${disruptionId}`);
    },

    async getPassengerProfile(passengerId) {
      return fetchJSON(`/passengers/${passengerId}/profile`);
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
      return fetchJSON(`/passengers/${passengerId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ optionId, disruptionId }),
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
