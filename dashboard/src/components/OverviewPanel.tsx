import { useState } from "react";
import type { Disruption, Passenger, Wish } from "../types";

interface Props {
  disruption: Disruption;
  passengers: Passenger[];
  pendingWishes: Wish[];
}

export function OverviewPanel({ disruption, passengers, pendingWishes }: Props) {
  const [collapsed, setCollapsed] = useState(false);

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
    <div className="bg-surface-800 border border-surface-600 rounded-lg">
      {/* Collapsed: compact single-line summary */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-surface-700/30 transition-colors rounded-lg"
      >
        <span
          className={`text-text-muted text-[10px] transition-transform ${
            collapsed ? "" : "rotate-90"
          }`}
        >
          ▶
        </span>
        <span className="inline-block px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-accent-red/20 text-accent-red uppercase">
          {disruption.type}
        </span>
        <span className="font-mono text-sm font-semibold text-text-primary">
          {disruption.flightNumber}
        </span>
        <span className="font-mono text-xs text-text-secondary">
          {disruption.origin} → {disruption.destination}
        </span>
        <span className="text-xs text-text-muted hidden sm:inline">—</span>
        <span className="text-xs text-text-muted hidden sm:inline truncate max-w-xs">
          {disruption.reason}
        </span>
        <div className="flex-1" />
        {/* Inline mini-stats when collapsed */}
        {collapsed && (
          <div className="flex items-center gap-3 text-[11px] font-mono shrink-0">
            <span className="text-accent-red">{affected} affected</span>
            <span className="text-text-muted">|</span>
            <span className="text-text-secondary">{notified} awaiting</span>
            <span className="text-text-muted">|</span>
            <span className={pendingWishes.length > 0 ? "text-accent-blue" : "text-text-secondary"}>
              {pendingWishes.length} pending
            </span>
            <span className="text-text-muted">|</span>
            <span className="text-accent-green">{approved} approved</span>
            {denied > 0 && (
              <>
                <span className="text-text-muted">|</span>
                <span className="text-accent-red">{denied} denied</span>
              </>
            )}
          </div>
        )}
        <span className="font-mono text-[10px] text-text-muted shrink-0 tabular-nums">
          {new Date(disruption.detectedAt).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </button>

      {/* Expanded: full stats */}
      {!collapsed && (
        <div className="px-5 pb-4 pt-1">
          <p className="text-sm text-text-secondary max-w-xl leading-relaxed mb-4">
            {disruption.reason}
          </p>
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
      )}
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
