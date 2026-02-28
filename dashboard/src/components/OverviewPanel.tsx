import type { Disruption, Passenger, Wish } from "../types";

interface Props {
  disruption: Disruption;
  passengers: Passenger[];
  pendingWishes: Wish[];
}

export function OverviewPanel({ disruption, passengers, pendingWishes }: Props) {
  const total = passengers.length;
  const affected = passengers.filter((p) => p.status !== "unaffected").length;
  const notified = passengers.filter((p) => p.status === "notified").length;
  const approved = passengers.filter((p) => p.status === "approved").length;
  const denied = passengers.filter((p) => p.denialCount > 0).length;
  const affectedPax = passengers.filter((p) => p.status !== "unaffected");
  const connecting = affectedPax.filter(
    (p) => p.originalItinerary.segments.length > 1
  ).length;
  const connectingPct = affected > 0 ? Math.round((connecting / affected) * 100) : 0;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-lg p-5">
      {/* Disruption header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-block px-2 py-0.5 text-xs font-mono font-semibold rounded bg-accent-red/20 text-accent-red uppercase">
              {disruption.type}
            </span>
            <span className="font-mono text-lg font-semibold text-text-primary">
              {disruption.flightNumber}
            </span>
            <span className="font-mono text-sm text-text-secondary">
              {disruption.origin} → {disruption.destination}
            </span>
          </div>
          <p className="text-sm text-text-secondary max-w-xl leading-relaxed">
            {disruption.reason}
          </p>
        </div>
        <div className="text-right font-mono text-xs text-text-muted shrink-0">
          Detected{" "}
          {new Date(disruption.detectedAt).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-6 gap-3">
        <StatCard label="Affected" value={affected} sublabel={`${total} total`} accent={affected > 0 ? "red" : undefined} />
        <StatCard
          label="Connecting"
          value={`${connectingPct}%`}
          sublabel={`${connecting} pax`}
          accent={connectingPct > 60 ? "amber" : undefined}
        />
        <StatCard label="Awaiting choice" value={notified} />
        <StatCard label="Pending approval" value={pendingWishes.length} accent={pendingWishes.length > 0 ? "blue" : undefined} />
        <StatCard label="Approved" value={approved} accent="green" />
        <StatCard label="Denied (escalated)" value={denied} accent={denied > 0 ? "red" : undefined} />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  accent?: "blue" | "green" | "amber" | "red";
}) {
  const accentColors = {
    blue: "text-accent-blue",
    green: "text-accent-green",
    amber: "text-accent-amber",
    red: "text-accent-red",
  };

  return (
    <div className="bg-surface-700 rounded-md px-3 py-2.5">
      <div
        className={`font-mono text-2xl font-semibold tabular-nums ${
          accent ? accentColors[accent] : "text-text-primary"
        }`}
      >
        {value}
      </div>
      <div className="text-xs text-text-muted mt-0.5">{label}</div>
      {sublabel && (
        <div className="text-xs text-text-muted mt-0.5">{sublabel}</div>
      )}
    </div>
  );
}
