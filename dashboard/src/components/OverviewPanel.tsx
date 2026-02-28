import { useState, useMemo, useRef, useEffect, type RefObject } from "react";
import type { Disruption, Passenger, Wish } from "../types";

interface Props {
  disruption: Disruption;
  passengers: Passenger[];
  pendingWishes: Wish[];
  disruptions: Disruption[];
  onSelectDisruption: (id: string) => void;
  flightSearchRef?: RefObject<HTMLInputElement | null>;
}

const TYPE_LABELS: Record<string, string> = {
  cancellation: "CNX",
  delay: "DLY",
  diversion: "DIV",
};

const TYPE_COLORS: Record<string, string> = {
  cancellation: "bg-accent-red/20 text-accent-red",
  delay: "bg-accent-amber/20 text-accent-amber",
  diversion: "bg-accent-blue/20 text-accent-blue",
};

export function OverviewPanel({ disruption, passengers, pendingWishes, disruptions, onSelectDisruption, flightSearchRef }: Props) {
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
    <div className="space-y-2">
      {/* Flight search */}
      <FlightSearch
        disruptions={disruptions}
        currentId={disruption.id}
        onSelect={onSelectDisruption}
        externalRef={flightSearchRef}
      />

      {/* Disruption detail */}
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
        <span className={`inline-block px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase ${TYPE_COLORS[disruption.type] ?? "bg-surface-600 text-text-muted"}`}>
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
    </div>
  );
}

function FlightSearch({
  disruptions,
  currentId,
  onSelect,
  externalRef,
}: {
  disruptions: Disruption[];
  currentId: string;
  onSelect: (id: string) => void;
  externalRef?: RefObject<HTMLInputElement | null>;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync external ref to internal input
  useEffect(() => {
    if (externalRef && "current" in externalRef) {
      (externalRef as React.MutableRefObject<HTMLInputElement | null>).current = inputRef.current;
    }
  });

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return disruptions;
    const q = query.toLowerCase();
    return disruptions.filter(
      (d) =>
        d.flightNumber.toLowerCase().includes(q) ||
        d.origin.toLowerCase().includes(q) ||
        d.destination.toLowerCase().includes(q) ||
        d.type.toLowerCase().includes(q) ||
        d.reason.toLowerCase().includes(q)
    );
  }, [disruptions, query]);

  const current = disruptions.find((d) => d.id === currentId);

  return (
    <div ref={ref} className="relative w-80">
      <div
        className={`flex items-center bg-surface-800 border rounded-md transition-colors ${
          open ? "border-accent-blue/50" : "border-surface-600"
        }`}
      >
        {/* Search icon */}
        <span className="pl-3 text-text-muted text-xs">✈</span>
        <input
          ref={inputRef}
          type="text"
          value={open ? query : ""}
          placeholder={
            open
              ? "Search by flight, route, type..."
              : current
                ? `${current.flightNumber}  ${current.origin} → ${current.destination}  ( F )`
                : "Select flight...  ( F )"
          }
          onFocus={() => {
            setOpen(true);
            setQuery("");
          }}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 bg-transparent px-2 py-1.5 text-xs font-mono text-text-primary placeholder:text-text-muted outline-none"
        />
        {open ? (
          <button
            onClick={() => { setOpen(false); setQuery(""); }}
            className="pr-3 text-text-muted hover:text-text-secondary text-xs cursor-pointer"
          >
            ✕
          </button>
        ) : (
          <span className="pr-3 text-text-muted text-[10px]">▼</span>
        )}
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-64 overflow-auto bg-surface-800 border border-surface-600 rounded-md shadow-xl">
          {filtered.length === 0 ? (
            <div className="px-3 py-4 text-xs text-text-muted text-center font-mono">
              No flights matching "{query}"
            </div>
          ) : (
            filtered.map((d) => (
              <button
                key={d.id}
                onClick={() => {
                  onSelect(d.id);
                  setOpen(false);
                  setQuery("");
                  inputRef.current?.blur();
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-mono transition-colors cursor-pointer ${
                  d.id === currentId
                    ? "bg-surface-700 text-text-primary"
                    : "text-text-secondary hover:bg-surface-700/50 hover:text-text-primary"
                }`}
              >
                <span className={`inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded uppercase shrink-0 ${TYPE_COLORS[d.type] ?? "bg-surface-600 text-text-muted"}`}>
                  {TYPE_LABELS[d.type] ?? d.type}
                </span>
                <span className="font-semibold shrink-0">{d.flightNumber}</span>
                <span className="text-text-muted shrink-0">{d.origin} → {d.destination}</span>
                <span className="flex-1" />
                <span className="text-text-muted truncate max-w-[140px] text-[10px]">{d.reason}</span>
              </button>
            ))
          )}
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
