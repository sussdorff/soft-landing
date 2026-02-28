import { useMemo, useState, type RefObject } from "react";
import type { Disruption, Passenger, Option, Wish } from "../types";
import { OptionDetailsDisplay } from "./OptionDetails";

interface Props {
  disruption: Disruption;
  passengers: Passenger[];
  optionsByPassenger: Map<string, Option[]>;
  wishesByPassenger: Map<string, Wish>;
  onViewProfile: (passengerId: string) => void;
  onResolve: (passengerId: string, optionId: string) => Promise<void>;
  searchRef?: RefObject<HTMLInputElement | null>;
}

const OPTION_TYPE_ICONS: Record<string, string> = {
  rebook: "plane",
  hotel: "hotel",
  ground: "train",
  alt_airport: "route",
  lounge: "armchair",
  voucher: "ticket",
};

const OPTION_TYPE_LABELS: Record<string, string> = {
  rebook: "Rebook",
  hotel: "Hotel + Flight",
  ground: "Ground Transport",
  alt_airport: "Alt. Route",
  lounge: "Lounge Access",
  voucher: "Meal Voucher",
};

type ImpactLevel = "disrupted" | "connection_at_risk" | "resolved" | "on_track";

function getImpactLevel(pax: Passenger, disruptedFlight: string): ImpactLevel {
  const isOnDisruptedFlight = pax.originalItinerary.segments.some(
    (s) => s.flightNumber === disruptedFlight
  );
  if (!isOnDisruptedFlight) return "on_track";
  if (pax.status === "approved") return "resolved";
  if (pax.status === "unaffected") return "on_track";
  if (pax.originalItinerary.segments.length > 1) return "connection_at_risk";
  return "disrupted";
}

function getImpactLabel(level: ImpactLevel): string {
  switch (level) {
    case "connection_at_risk":
      return "Connection at risk";
    case "disrupted":
      return "Disrupted";
    case "resolved":
      return "Resolved";
    case "on_track":
      return "On track";
  }
}

function getFinalDestination(pax: Passenger): string {
  const segs = pax.originalItinerary.segments;
  return segs[segs.length - 1]?.destination ?? "—";
}

export function FlightOverview({
  disruption,
  passengers,
  optionsByPassenger,
  wishesByPassenger,
  onViewProfile,
  onResolve,
  searchRef,
}: Props) {
  const [expandedPax, setExpandedPax] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [headerCollapsed, setHeaderCollapsed] = useState(false);

  const toggle = (id: string) => {
    setExpandedPax((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Sort: connection_at_risk first, then disrupted, then resolved, then on_track; within group by name
  const sorted = useMemo(() => {
    const q = search.toLowerCase().trim();
    const filtered = q
      ? passengers.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            p.bookingRef.toLowerCase().includes(q) ||
            p.originalItinerary.segments.some(
              (s) =>
                s.origin.toLowerCase().includes(q) ||
                s.destination.toLowerCase().includes(q) ||
                s.flightNumber.toLowerCase().includes(q)
            )
        )
      : passengers;

    return [...filtered].sort((a, b) => {
      const order: Record<ImpactLevel, number> = {
        connection_at_risk: 0,
        disrupted: 1,
        resolved: 2,
        on_track: 3,
      };
      const diff =
        order[getImpactLevel(a, disruption.flightNumber)] -
        order[getImpactLevel(b, disruption.flightNumber)];
      if (diff !== 0) return diff;
      return a.name.localeCompare(b.name);
    });
  }, [passengers, search, disruption.flightNumber]);

  const expandAll = () => {
    setExpandedPax(new Set(sorted.map((p) => p.id)));
  };

  const collapseAll = () => {
    setExpandedPax(new Set());
  };

  const atRisk = passengers.filter(
    (p) => getImpactLevel(p, disruption.flightNumber) === "connection_at_risk"
  ).length;
  const disrupted = passengers.filter(
    (p) => getImpactLevel(p, disruption.flightNumber) === "disrupted"
  ).length;
  const resolved = passengers.filter(
    (p) => getImpactLevel(p, disruption.flightNumber) === "resolved"
  ).length;
  const onTrack = passengers.filter(
    (p) => getImpactLevel(p, disruption.flightNumber) === "on_track"
  ).length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-3 border-b border-surface-600 shrink-0">
        {/* Disruption summary + impact pills — collapsible */}
        {!headerCollapsed && (
          <>
            <div className="bg-surface-900/50 rounded-md px-4 py-3 mb-3">
              <p className="text-sm text-text-secondary leading-relaxed">
                {disruption.explanation}
              </p>
            </div>
            <div className="flex items-center gap-3 mb-3">
              <ImpactPill
                color="amber"
                count={atRisk}
                label="Connections at risk"
              />
              <ImpactPill color="red" count={disrupted} label="Disrupted" />
              <ImpactPill color="green" count={resolved} label="Resolved" />
              <ImpactPill color="slate" count={onTrack} label="On track" />
            </div>
          </>
        )}

        {/* Toolbar: search + controls — always visible */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-xs pointer-events-none">
              /
            </span>
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder='Search by name, PNR, airport, or flight...  ( / )'
              className="w-full bg-surface-900/60 border border-surface-600 rounded-md pl-7 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted/50 font-mono focus:outline-none focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/20 transition-colors"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary text-xs font-mono cursor-pointer"
              >
                clear
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setHeaderCollapsed(!headerCollapsed)}
              className="text-[10px] font-mono text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
            >
              {headerCollapsed ? "Show summary" : "Hide summary"}
            </button>
            <span className="text-text-muted">|</span>
            <button
              onClick={expandAll}
              className="px-3 py-1.5 text-xs font-mono font-semibold text-text-secondary bg-surface-700 hover:bg-surface-600 rounded-md transition-colors cursor-pointer"
            >
              Expand all
            </button>
            <button
              onClick={collapseAll}
              className="px-3 py-1.5 text-xs font-mono font-semibold text-text-secondary bg-surface-700 hover:bg-surface-600 rounded-md transition-colors cursor-pointer"
            >
              Collapse all
            </button>
          </div>
        </div>
      </div>

      {/* Passenger list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1.5">
        {sorted.length === 0 && search && (
          <div className="text-sm text-text-muted text-center py-8 font-mono">
            No passengers matching "{search}"
          </div>
        )}
        {sorted.map((pax) => {
          const impact = getImpactLevel(pax, disruption.flightNumber);
          const options = optionsByPassenger.get(pax.id) ?? [];
          const wish = wishesByPassenger.get(pax.id);
          const isExpanded = expandedPax.has(pax.id);

          return (
            <PassengerRow
              key={pax.id}
              passenger={pax}
              impact={impact}
              options={options}
              wish={wish}
              expanded={isExpanded}
              onToggle={() => toggle(pax.id)}
              onViewProfile={() => onViewProfile(pax.id)}
              onResolve={onResolve}
              disruptedFlight={disruption.flightNumber}
              disruptionType={disruption.type}
            />
          );
        })}
      </div>
    </div>
  );
}

function PassengerRow({
  passenger,
  impact,
  options,
  wish,
  expanded,
  onToggle,
  onViewProfile,
  onResolve,
  disruptedFlight,
  disruptionType,
}: {
  passenger: Passenger;
  impact: ImpactLevel;
  options: Option[];
  wish: Wish | undefined;
  expanded: boolean;
  onToggle: () => void;
  onViewProfile: () => void;
  onResolve: (passengerId: string, optionId: string) => Promise<void>;
  disruptedFlight: string;
  disruptionType: string;
}) {
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const impactStyles: Record<ImpactLevel, string> = {
    connection_at_risk: "border-l-accent-amber",
    disrupted: "border-l-accent-red",
    resolved: "border-l-accent-green",
    on_track: "border-l-surface-500",
  };

  const impactBadgeStyles: Record<ImpactLevel, string> = {
    connection_at_risk: "bg-accent-amber/15 text-accent-amber",
    disrupted: "bg-accent-red/15 text-accent-red",
    resolved: "bg-accent-green/15 text-accent-green",
    on_track: "bg-surface-600 text-text-muted",
  };

  const statusBadgeStyles: Record<string, string> = {
    notified: "bg-accent-blue/15 text-accent-blue",
    chose: "bg-accent-purple/15 text-accent-purple",
    approved: "bg-accent-green/15 text-accent-green",
    denied: "bg-accent-red/15 text-accent-red",
  };

  const finalDest = getFinalDestination(passenger);
  const segments = passenger.originalItinerary.segments;
  const isMultiLeg = segments.length > 1;

  // Find which option the passenger chose (if any)
  const chosenOption = wish
    ? options.find((o) => o.id === wish.selectedOptionId)
    : undefined;

  return (
    <div
      className={`border-l-[3px] rounded-r-md bg-surface-700 transition-colors ${impactStyles[impact]}`}
    >
      {/* Summary row — always visible */}
      <div
        className="flex items-center px-4 py-2.5 cursor-pointer hover:bg-surface-600/30 transition-colors"
        onClick={onToggle}
      >
        {/* Expand arrow */}
        <span
          className={`text-text-muted text-[10px] mr-3 transition-transform ${
            expanded ? "rotate-90" : ""
          }`}
        >
          ▶
        </span>

        {/* Name + PNR */}
        <div className="w-44 shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewProfile();
            }}
            className="text-sm font-semibold text-text-primary hover:text-accent-blue transition-colors cursor-pointer"
          >
            {passenger.name}
          </button>
          <div className="font-mono text-[10px] text-text-muted">
            {passenger.bookingRef}
          </div>
        </div>

        {/* Journey: origin → [segments] → final dest */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1 font-mono text-xs text-text-secondary">
            {segments.map((seg, i) => (
              <span key={i} className="flex items-center gap-1">
                {i === 0 && (
                  <span className="text-text-primary">{seg.origin}</span>
                )}
                <span className="text-text-muted">→</span>
                {seg.flightNumber === disruptedFlight ? (
                  <span className={`px-1 py-0.5 rounded ${
                    disruptionType === "cancellation"
                      ? "bg-accent-red/15 text-accent-red line-through"
                      : "bg-accent-amber/15 text-accent-amber"
                  }`}>
                    {seg.flightNumber}
                  </span>
                ) : (
                  <span className="text-text-muted">{seg.flightNumber}</span>
                )}
                <span className="text-text-muted">→</span>
                <span
                  className={
                    i === segments.length - 1
                      ? "text-text-primary"
                      : "text-text-muted"
                  }
                >
                  {seg.destination}
                </span>
              </span>
            ))}
          </div>
        </div>

        {/* Impact badge */}
        <span
          className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase tracking-wider shrink-0 mx-2 ${impactBadgeStyles[impact]}`}
        >
          {getImpactLabel(impact)}
        </span>

        {/* Status badge */}
        <span
          className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase tracking-wider shrink-0 ${
            statusBadgeStyles[passenger.status] ??
            "bg-surface-600 text-text-muted"
          }`}
        >
          {passenger.status}
        </span>

        {/* Denial count */}
        {passenger.denialCount > 0 && (
          <span className="ml-2 px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-accent-red/20 text-accent-red shrink-0">
            {passenger.denialCount}x denied
          </span>
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-3 pt-0 border-t border-surface-600/50">
          {/* Journey detail */}
          {(isMultiLeg || impact === "on_track") && (
            <div className="mt-3 mb-3">
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                {impact === "on_track"
                  ? `Journey — ${segments[0]?.origin} → ${finalDest}`
                  : `Full Journey — Final destination: ${finalDest}`}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {segments.map((seg, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono ${
                      seg.flightNumber === disruptedFlight
                        ? disruptionType === "cancellation"
                          ? "bg-accent-red/10 border border-accent-red/30"
                          : "bg-accent-amber/10 border border-accent-amber/30"
                        : "bg-surface-800"
                    }`}
                  >
                    <span
                      className={
                        seg.flightNumber === disruptedFlight
                          ? disruptionType === "cancellation"
                            ? "font-semibold text-accent-red"
                            : "font-semibold text-accent-amber"
                          : "text-text-primary"
                      }
                    >
                      {seg.flightNumber}
                    </span>
                    <span className="text-text-muted">
                      {seg.origin}→{seg.destination}
                    </span>
                    <span className="text-text-muted tabular-nums">
                      {new Date(seg.departure).toLocaleTimeString("en-GB", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {seg.flightNumber === disruptedFlight && (
                      <span className={
                        disruptionType === "cancellation"
                          ? "text-accent-red font-semibold"
                          : "text-accent-amber font-semibold"
                      }>
                        {disruptionType === "cancellation" ? "CANCELLED" : "DELAYED"}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* On-track passengers: nothing else to show */}
          {impact === "on_track" && (
            <div className="text-xs text-text-muted px-1 py-1">
              No action needed — journey is unaffected by this disruption.
            </div>
          )}

          {/* Passenger's choice (if they chose) */}
          {impact !== "on_track" && wish && chosenOption && (
            <div className="mb-3">
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Passenger's choice
              </div>
              <div className="flex items-center gap-2 px-3 py-2 rounded bg-accent-purple/10 border border-accent-purple/20">
                <OptionTypeIcon type={chosenOption.type} />
                <div className="flex-1">
                  <div className="text-sm text-text-primary">
                    {chosenOption.summary}
                  </div>
                  <div className="text-xs text-text-muted">
                    {chosenOption.description}
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase ${
                    wish.status === "approved"
                      ? "bg-accent-green/15 text-accent-green"
                      : wish.status === "denied"
                      ? "bg-accent-red/15 text-accent-red"
                      : "bg-accent-amber/15 text-accent-amber"
                  }`}
                >
                  {wish.status}
                </span>
              </div>
              {wish.confirmationDetails && (
                <div className="text-xs text-accent-green/80 mt-1 ml-3">
                  {wish.confirmationDetails}
                </div>
              )}
              {wish.denialReason && (
                <div className="text-xs text-accent-red/80 mt-1 ml-3">
                  Denied: {wish.denialReason}
                </div>
              )}
            </div>
          )}

          {/* Suggested options (only for affected passengers) */}
          {impact !== "on_track" && <div>
            <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
              Suggested options ({options.length})
            </div>
            <div className="space-y-1">
              {options.map((opt) => {
                const isResolved = impact === "resolved";
                const isChosen = chosenOption?.id === opt.id;
                const canResolve = opt.available && !isResolved;

                return (
                  <div
                    key={opt.id}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded text-sm ${
                      opt.available
                        ? "bg-surface-800"
                        : "bg-surface-800/50 opacity-50"
                    } ${isChosen ? "ring-1 ring-accent-purple/40" : ""}`}
                  >
                    {canResolve ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setResolvingId(opt.id);
                          onResolve(passenger.id, opt.id).finally(() =>
                            setResolvingId(null)
                          );
                        }}
                        disabled={resolvingId !== null}
                        className={`shrink-0 px-5 py-2.5 text-sm font-mono font-bold rounded-md transition-all cursor-pointer ${
                          resolvingId === opt.id
                            ? "bg-accent-green text-surface-900 scale-95"
                            : "bg-accent-green text-surface-900 hover:brightness-110 hover:shadow-[0_0_12px_rgba(34,197,94,0.4)] active:scale-95"
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        {resolvingId === opt.id ? "..." : "RESOLVE"}
                      </button>
                    ) : (
                      <span className="shrink-0 w-[100px]" />
                    )}
                    <OptionTypeIcon type={opt.type} />
                    <div className="flex-1 min-w-0">
                      <div className="text-text-primary truncate">
                        {opt.summary}
                      </div>
                      <div className="text-xs text-text-muted truncate">
                        <OptionDetailsDisplay option={opt} />
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-mono text-xs text-text-secondary tabular-nums">
                        ETA{" "}
                        {new Date(opt.estimatedArrival).toLocaleString("en-GB", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      {!opt.available && (
                        <div className="text-[10px] font-mono text-accent-amber">
                          UNAVAILABLE
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {options.length === 0 && (
                <div className="text-xs text-text-muted px-3 py-2">
                  Options being generated...
                </div>
              )}
            </div>
          </div>}
        </div>
      )}
    </div>
  );
}

function OptionTypeIcon({ type }: { type: string }) {
  const icons: Record<string, string> = OPTION_TYPE_ICONS;
  const labels: Record<string, string> = OPTION_TYPE_LABELS;

  const colors: Record<string, string> = {
    rebook: "bg-accent-blue/15 text-accent-blue",
    hotel: "bg-accent-amber/15 text-accent-amber",
    ground: "bg-accent-green/15 text-accent-green",
    alt_airport: "bg-accent-purple/15 text-accent-purple",
    lounge: "bg-accent-cyan/15 text-accent-cyan",
    voucher: "bg-accent-orange/15 text-accent-orange",
  };

  return (
    <span
      className={`shrink-0 px-2 py-1 text-[10px] font-mono font-semibold rounded uppercase tracking-wider ${
        colors[type] ?? "bg-surface-600 text-text-muted"
      }`}
      title={labels[type] ?? type}
    >
      {icons[type] ?? "•"} {labels[type] ?? type}
    </span>
  );
}

function ImpactPill({
  color,
  count,
  label,
}: {
  color: "amber" | "red" | "green" | "slate";
  count: number;
  label: string;
}) {
  const styles = {
    amber: "bg-accent-amber/10 text-accent-amber border-accent-amber/20",
    red: "bg-accent-red/10 text-accent-red border-accent-red/20",
    green: "bg-accent-green/10 text-accent-green border-accent-green/20",
    slate: "bg-surface-600/50 text-text-muted border-surface-500",
  };

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-mono ${styles[color]}`}
    >
      <span className="font-bold tabular-nums">{count}</span>
      <span className="opacity-80">{label}</span>
    </div>
  );
}
