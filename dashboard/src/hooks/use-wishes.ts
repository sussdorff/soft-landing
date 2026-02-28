import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Wish, WSEvent } from "../types";

export function useWishes(disruptionId: string) {
  const [wishes, setWishes] = useState<Wish[]>([]);
  const [loading, setLoading] = useState(true);

  // Initial fetch
  useEffect(() => {
    let cancelled = false;
    api.getWishes(disruptionId).then((w) => {
      if (!cancelled) {
        setWishes(w);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [disruptionId]);

  // Live updates via WebSocket / mock events
  useEffect(() => {
    const unsub = api.onEvent((event: WSEvent) => {
      if (event.type === "new_wish") {
        const newWish = event.data as Wish;
        setWishes((prev) => [newWish, ...prev]);
      } else if (event.type === "wish_approved" || event.type === "wish_denied") {
        const updated = event.data as Wish;
        setWishes((prev) =>
          prev.map((w) => (w.id === updated.id ? updated : w))
        );
      }
    });
    return unsub;
  }, []);

  const approve = useCallback(async (wishId: string) => {
    await api.approveWish(wishId);
    // Optimistic update — also gets confirmed via WS event
    setWishes((prev) =>
      prev.map((w) =>
        w.id === wishId ? { ...w, status: "approved" as const } : w
      )
    );
  }, []);

  const deny = useCallback(async (wishId: string, reason: string) => {
    await api.denyWish(wishId, reason);
    setWishes((prev) =>
      prev.map((w) =>
        w.id === wishId
          ? { ...w, status: "denied" as const, denialReason: reason }
          : w
      )
    );
  }, []);

  const resolveManually = useCallback(
    async (passengerId: string, optionId: string) => {
      const wish = await api.resolveManually(passengerId, optionId, disruptionId);
      setWishes((prev) => [wish, ...prev]);
    },
    [disruptionId]
  );

  const pendingWishes = wishes.filter((w) => w.status === "pending");
  const resolvedWishes = wishes.filter((w) => w.status !== "pending");

  return { wishes, pendingWishes, resolvedWishes, loading, approve, deny, resolveManually };
}
