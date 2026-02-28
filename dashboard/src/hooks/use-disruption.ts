import { useEffect, useState } from "react";
import { api } from "../api";
import type { Disruption, Passenger, WSEvent } from "../types";

export function useDisruption(disruptionId: string) {
  const [disruption, setDisruption] = useState<Disruption | null>(null);
  const [passengers, setPassengers] = useState<Passenger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      api.getDisruption(disruptionId),
      api.getPassengers(disruptionId),
    ])
      .then(([d, p]) => {
        if (cancelled) return;
        setDisruption(d);
        setPassengers(p);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [disruptionId]);

  // Re-fetch passengers when wish status changes (approve/deny/resolve)
  useEffect(() => {
    const unsub = api.onEvent((event: WSEvent) => {
      if (
        event.type === "wish_approved" ||
        event.type === "wish_denied"
      ) {
        api.getPassengers(disruptionId).then(setPassengers);
      }
    });
    return unsub;
  }, [disruptionId]);

  return { disruption, passengers, loading, error };
}
