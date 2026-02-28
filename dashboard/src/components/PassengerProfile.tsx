import { useEffect, useState } from "react";
import { api } from "../api";
import type { PassengerProfile as Profile } from "../types";
import { OptionDetailsDisplay } from "./OptionDetails";

interface Props {
  passengerId: string;
  onClose: () => void;
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  rebook: "Flight Rebook",
  hotel: "Hotel + Next Day",
  ground: "Ground Transport",
  alt_airport: "Alt. Airport Route",
  lounge: "Lounge Access",
  voucher: "Meal Voucher",
};

export function PassengerProfile({ passengerId, onClose }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.getPassengerProfile(passengerId).then((p) => {
      if (!cancelled) {
        setProfile(p);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [passengerId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-800 border border-surface-600 rounded-lg w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-surface-600 sticky top-0 bg-surface-800">
          <h2 className="text-lg font-semibold text-text-primary">
            Passenger Profile
          </h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-xl leading-none transition-colors cursor-pointer"
          >
            &times;
          </button>
        </div>

        {loading || !profile ? (
          <div className="p-8 text-center text-text-muted">Loading...</div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Identity */}
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xl font-semibold text-text-primary">
                  {profile.name}
                </div>
                <div className="font-mono text-sm text-text-secondary mt-1">
                  {profile.bookingRef}
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-2">
                  <StatusBadge status={profile.status} />
                  {profile.denialCount > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-accent-red/20 text-accent-red">
                      {profile.denialCount}x denied
                    </span>
                  )}
                </div>
                <div className="font-mono text-xs text-text-muted mt-1">
                  Priority: {profile.priority}
                </div>
              </div>
            </div>

            {/* Itinerary */}
            <section>
              <h3 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-2">
                Original Itinerary
              </h3>
              <div className="space-y-1.5">
                {profile.originalItinerary.segments.map((seg, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-3 py-2 bg-surface-700 rounded text-sm"
                  >
                    <span className="font-mono font-semibold text-text-primary">
                      {seg.flightNumber}
                    </span>
                    <span className="font-mono text-text-secondary">
                      {seg.origin} → {seg.destination}
                    </span>
                    <span className="font-mono text-xs text-text-muted ml-auto tabular-nums">
                      {new Date(seg.departure).toLocaleString("en-GB", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* Related disruptions */}
            {profile.disruptions && profile.disruptions.length > 0 && (
              <section>
                <h3 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-2">
                  Related Disruptions ({profile.disruptions.length})
                </h3>
                <div className="space-y-1.5">
                  {profile.disruptions.map((d) => (
                    <div
                      key={d.id}
                      className="px-3 py-2 bg-surface-700 rounded text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-red/15 text-accent-red uppercase">
                          {d.type}
                        </span>
                        <span className="font-mono font-semibold text-text-primary">
                          {d.flightNumber}
                        </span>
                        <span className="font-mono text-text-secondary">
                          {d.origin} → {d.destination}
                        </span>
                      </div>
                      <div className="text-text-secondary mt-1">
                        {d.reason}
                      </div>
                      <div className="font-mono text-[10px] text-text-muted mt-1 tabular-nums">
                        {new Date(d.detectedAt).toLocaleString("en-GB", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Available options */}
            <section>
              <h3 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-2">
                Available Options ({profile.options.length})
              </h3>
              <div className="space-y-1.5">
                {profile.options.map((opt) => (
                  <div
                    key={opt.id}
                    className={`px-3 py-2 rounded text-sm ${
                      opt.available
                        ? "bg-surface-700"
                        : "bg-surface-700/50 opacity-60"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-surface-600 text-text-secondary">
                        {OPTION_TYPE_LABELS[opt.type] ?? opt.type}
                      </span>
                      {!opt.available && (
                        <span className="text-[10px] font-mono text-accent-amber">
                          UNAVAILABLE
                        </span>
                      )}
                    </div>
                    <div className="text-text-primary mt-1">{opt.summary}</div>
                    <div className="text-xs text-text-muted mt-0.5">
                      <OptionDetailsDisplay option={opt} />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Wish history */}
            <section>
              <h3 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-2">
                Wish History ({profile.wishes.length})
              </h3>
              {profile.wishes.length === 0 ? (
                <div className="text-sm text-text-muted px-3">
                  No wishes submitted
                </div>
              ) : (
                <div className="space-y-1.5">
                  {profile.wishes.map((w) => (
                    <div
                      key={w.id}
                      className="px-3 py-2 bg-surface-700 rounded text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <StatusBadge status={w.status} />
                        <span className="font-mono text-[10px] text-text-muted tabular-nums">
                          {new Date(w.submittedAt).toLocaleString("en-GB", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <div className="text-xs text-text-secondary mt-1">
                        Selected: {w.selectedOptionId}
                      </div>
                      {w.denialReason && (
                        <div className="text-xs text-accent-red/80 mt-1">
                          Denied: {w.denialReason}
                        </div>
                      )}
                      {w.confirmationDetails && (
                        <div className="text-xs text-accent-green/80 mt-1">
                          {w.confirmationDetails}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    unaffected: "bg-surface-600 text-text-muted",
    notified: "bg-accent-blue/15 text-accent-blue",
    chose: "bg-accent-purple/15 text-accent-purple",
    pending: "bg-accent-amber/15 text-accent-amber",
    approved: "bg-accent-green/15 text-accent-green",
    denied: "bg-accent-red/15 text-accent-red",
  };

  return (
    <span
      className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase tracking-wider ${
        styles[status] ?? styles.unaffected
      }`}
    >
      {status}
    </span>
  );
}
