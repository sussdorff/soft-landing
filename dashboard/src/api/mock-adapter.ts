import type { DashboardAPI, WSEvent, Wish } from "../types";
import {
  DISRUPTION,
  PASSENGERS,
  WISHES,
  buildPassengerProfile,
} from "./mock-data";

// Simulated latency to feel realistic
const delay = (ms = 200) => new Promise((r) => setTimeout(r, ms));

export function createMockAdapter(): DashboardAPI {
  // Mutable copy so approve/deny actually update state
  const wishes: Wish[] = [...WISHES];
  const eventHandlers: Set<(event: WSEvent) => void> = new Set();

  function emit(event: WSEvent) {
    eventHandlers.forEach((h) => h(event));
  }

  // Simulate a new wish arriving every 15s
  let simInterval: ReturnType<typeof setInterval> | null = null;
  const simPassengers = ["pax-006", "pax-007", "pax-009", "pax-011"];
  let simIndex = 0;

  function startSimulation() {
    if (simInterval) return;
    simInterval = setInterval(() => {
      if (simIndex >= simPassengers.length) {
        if (simInterval) clearInterval(simInterval);
        return;
      }
      const paxId = simPassengers[simIndex++];
      const newWish: Wish = {
        id: `wish-sim-${Date.now()}`,
        passengerId: paxId,
        disruptionId: "dis-001",
        selectedOptionId: "opt-002a",
        rankedOptionIds: ["opt-002a", "opt-002b"],
        submittedAt: new Date().toISOString(),
        status: "pending",
      };
      wishes.push(newWish);
      emit({
        type: "new_wish",
        timestamp: newWish.submittedAt,
        data: newWish,
      });
    }, 15000);
  }

  return {
    async getDisruption() {
      await delay();
      return DISRUPTION;
    },

    async getPassengers() {
      await delay();
      // Sort by priority desc, then by name
      return [...PASSENGERS].sort(
        (a, b) => b.priority - a.priority || a.name.localeCompare(b.name)
      );
    },

    async getWishes() {
      await delay();
      // Sort: pending first (by priority desc, then submittedAt asc), then approved/denied
      const paxMap = new Map(PASSENGERS.map((p) => [p.id, p]));
      return [...wishes].sort((a, b) => {
        // Pending before resolved
        const aResolved = a.status !== "pending" ? 1 : 0;
        const bResolved = b.status !== "pending" ? 1 : 0;
        if (aResolved !== bResolved) return aResolved - bResolved;
        // Within pending: higher priority first
        const aPriority = paxMap.get(a.passengerId)?.priority ?? 0;
        const bPriority = paxMap.get(b.passengerId)?.priority ?? 0;
        if (aPriority !== bPriority) return bPriority - aPriority;
        // Then by submission time
        return a.submittedAt.localeCompare(b.submittedAt);
      });
    },

    async getPassengerProfile(passengerId: string) {
      await delay(300);
      return buildPassengerProfile(passengerId);
    },

    async approveWish(wishId: string) {
      await delay(400);
      const wish = wishes.find((w) => w.id === wishId);
      if (wish) {
        wish.status = "approved";
        wish.confirmationDetails = "Approved by gate agent. Booking confirmed.";
        const pax = PASSENGERS.find((p) => p.id === wish.passengerId);
        if (pax) pax.status = "approved";
        emit({
          type: "wish_approved",
          timestamp: new Date().toISOString(),
          data: wish,
        });
      }
    },

    async denyWish(wishId: string, reason: string) {
      await delay(400);
      const wish = wishes.find((w) => w.id === wishId);
      if (wish) {
        wish.status = "denied";
        wish.denialReason = reason;
        const pax = PASSENGERS.find((p) => p.id === wish.passengerId);
        if (pax) {
          pax.status = "denied";
          pax.denialCount += 1;
          pax.priority = Math.min(pax.denialCount, 2);
        }
        emit({
          type: "wish_denied",
          timestamp: new Date().toISOString(),
          data: wish,
        });
      }
    },

    async resolveManually(passengerId: string, optionId: string, disruptionId: string) {
      await delay(400);
      const newWish: Wish = {
        id: `wish-manual-${Date.now()}`,
        passengerId,
        disruptionId,
        selectedOptionId: optionId,
        rankedOptionIds: [optionId],
        submittedAt: new Date().toISOString(),
        status: "approved",
        confirmationDetails: "Manually resolved by gate agent.",
      };
      wishes.push(newWish);
      const pax = PASSENGERS.find((p) => p.id === passengerId);
      if (pax) pax.status = "approved";
      emit({
        type: "wish_approved",
        timestamp: new Date().toISOString(),
        data: newWish,
      });
      return newWish;
    },

    onEvent(handler) {
      eventHandlers.add(handler);
      startSimulation();
      return () => {
        eventHandlers.delete(handler);
        if (eventHandlers.size === 0 && simInterval) {
          clearInterval(simInterval);
          simInterval = null;
        }
      };
    },
  };
}
