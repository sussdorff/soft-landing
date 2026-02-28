import { useState } from "react";
import type { Wish, Passenger, Option } from "../types";

interface Props {
  wish: Wish;
  passenger: Passenger | undefined;
  selectedOption: Option | undefined;
  allOptions: Option[];
  onViewProfile: (passengerId: string) => void;
  onResolve: (passengerId: string, optionId: string) => Promise<void>;
  onRefreshOptions: (passengerId: string) => Promise<Option[]>;
}

const OPTION_TYPE_ICONS: Record<string, string> = {
  rebook: "✈",
  hotel: "🏨",
  ground: "🚄",
  alt_airport: "↗",
  lounge: "🛋",
  voucher: "🎫",
};

export function ResolvedCard({
  wish,
  passenger,
  selectedOption,
  allOptions,
  onViewProfile,
  onResolve,
  onRefreshOptions,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [freshOptions, setFreshOptions] = useState<Option[] | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  if (!passenger) return null;

  const statusBadge =
    wish.status === "approved" ? (
      <span className="px-2 py-0.5 text-xs font-mono rounded bg-accent-green/20 text-accent-green">
        APPROVED
      </span>
    ) : (
      <span className="px-2 py-0.5 text-xs font-mono rounded bg-accent-red/20 text-accent-red">
        DENIED
      </span>
    );

  const handleEdit = async () => {
    setEditing(true);
    setRefreshing(true);
    try {
      const options = await onRefreshOptions(passenger.id);
      setFreshOptions(options);
    } catch {
      // Fall back to existing options if refresh fails
      setFreshOptions(allOptions);
    } finally {
      setRefreshing(false);
    }
  };

  const handleResolve = async (optionId: string) => {
    setResolvingId(optionId);
    try {
      await onResolve(passenger.id, optionId);
      setEditing(false);
      setFreshOptions(null);
    } finally {
      setResolvingId(null);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setFreshOptions(null);
  };

  const displayOptions = freshOptions ?? allOptions;

  return (
    <div className="border-l-[3px] border-l-surface-500 rounded-r-md bg-surface-700 px-4 py-3 transition-colors">
      {/* Top row: passenger info + status */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          {passenger.priority >= 2 && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-accent-red/20 text-accent-red uppercase tracking-wider">
              P{passenger.denialCount}
            </span>
          )}
          {passenger.priority === 1 && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-accent-amber/20 text-accent-amber uppercase tracking-wider">
              P1
            </span>
          )}

          <button
            onClick={() => onViewProfile(passenger.id)}
            className="text-sm font-semibold text-text-primary hover:text-accent-blue transition-colors cursor-pointer"
          >
            {passenger.name}
          </button>
          <span className="font-mono text-xs text-text-muted">
            {passenger.bookingRef}
          </span>

          <span className="font-mono text-xs text-text-secondary">
            {passenger.originalItinerary.segments
              .map((s) => s.origin)
              .concat(
                passenger.originalItinerary.segments[
                  passenger.originalItinerary.segments.length - 1
                ]?.destination ?? ""
              )
              .join(" → ")}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {statusBadge}
          <span className="font-mono text-[10px] text-text-muted tabular-nums">
            {new Date(wish.submittedAt).toLocaleTimeString("en-GB", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>

      {/* Selected option */}
      {selectedOption && (
        <div className="flex items-center gap-2 mb-2 ml-1">
          <span className="text-sm" role="img">
            {OPTION_TYPE_ICONS[selectedOption.type] ?? "•"}
          </span>
          <span className="text-sm text-text-primary">
            {selectedOption.summary}
          </span>
        </div>
      )}

      {/* Denial reason */}
      {wish.status === "denied" && wish.denialReason && (
        <div className="text-xs text-accent-red/80 ml-1 mb-2">
          Reason: {wish.denialReason}
        </div>
      )}

      {/* Confirmation details */}
      {wish.status === "approved" && wish.confirmationDetails && (
        <div className="text-xs text-accent-green/80 ml-1 mb-2">
          {wish.confirmationDetails}
        </div>
      )}

      {/* Edit button or edit panel */}
      {!editing ? (
        <div className="mt-3 pt-3 border-t border-surface-600/50">
          <button
            onClick={handleEdit}
            className="px-4 py-2 text-xs font-semibold rounded-md bg-surface-600 text-text-secondary hover:bg-surface-500 hover:text-text-primary transition-all cursor-pointer"
          >
            EDIT RESOLUTION
          </button>
        </div>
      ) : (
        <div className="mt-3 pt-3 border-t border-surface-600/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
              {refreshing ? "Refreshing options..." : "Select new option"}
            </span>
            <button
              onClick={handleCancel}
              className="text-xs text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </div>

          {refreshing ? (
            <div className="flex items-center gap-2 py-3 text-text-muted text-sm">
              <div className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
              Loading fresh options...
            </div>
          ) : (
            <div className="space-y-1">
              {displayOptions.map((opt) => (
                <div
                  key={opt.id}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-sm ${
                    opt.available
                      ? "bg-surface-800"
                      : "bg-surface-800/50 opacity-50"
                  }`}
                >
                  {opt.available ? (
                    <button
                      onClick={() => handleResolve(opt.id)}
                      disabled={resolvingId !== null}
                      className={`shrink-0 px-4 py-2 text-xs font-mono font-bold rounded-md transition-all cursor-pointer ${
                        resolvingId === opt.id
                          ? "bg-accent-green text-surface-900 scale-95"
                          : "bg-accent-green text-surface-900 hover:brightness-110 hover:shadow-[0_0_12px_rgba(34,197,94,0.4)] active:scale-95"
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {resolvingId === opt.id ? "..." : "SELECT"}
                    </button>
                  ) : (
                    <span className="shrink-0 w-[76px]" />
                  )}
                  <span className="text-sm" role="img">
                    {OPTION_TYPE_ICONS[opt.type] ?? "•"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-text-primary truncate">
                      {opt.summary}
                    </div>
                    <div className="text-xs text-text-muted truncate">
                      {opt.description}
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
              ))}
              {displayOptions.length === 0 && (
                <div className="text-xs text-text-muted px-3 py-2">
                  No options available for this passenger.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
