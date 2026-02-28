import { useState } from "react";
import type { Wish, Passenger, Option } from "../types";

interface Props {
  wish: Wish;
  passenger: Passenger | undefined;
  selectedOption: Option | undefined;
  onApprove: (wishId: string) => void;
  onDeny: (wishId: string, reason: string) => void;
  onViewProfile: (passengerId: string) => void;
}

const OPTION_TYPE_ICONS: Record<string, string> = {
  rebook: "✈",
  hotel: "🏨",
  ground: "🚄",
  alt_airport: "↗",
  lounge: "🛋",
  voucher: "🎫",
};

export function WishCard({
  wish,
  passenger,
  selectedOption,
  onApprove,
  onDeny,
  onViewProfile,
}: Props) {
  const [showDenyInput, setShowDenyInput] = useState(false);
  const [denyReason, setDenyReason] = useState("");
  const [acting, setActing] = useState(false);

  if (!passenger) return null;

  const priorityStyles = {
    0: "border-l-surface-600",
    1: "border-l-accent-amber bg-priority-elevated/30",
    2: "border-l-accent-red bg-priority-critical/30",
  };

  const statusBadge = {
    pending: null,
    approved: (
      <span className="px-2 py-0.5 text-xs font-mono rounded bg-accent-green/20 text-accent-green">
        APPROVED
      </span>
    ),
    denied: (
      <span className="px-2 py-0.5 text-xs font-mono rounded bg-accent-red/20 text-accent-red">
        DENIED
      </span>
    ),
  };

  const handleApprove = async () => {
    setActing(true);
    await onApprove(wish.id);
    setActing(false);
  };

  const handleDeny = async () => {
    if (!denyReason.trim()) return;
    setActing(true);
    await onDeny(wish.id, denyReason);
    setActing(false);
    setShowDenyInput(false);
  };

  const isPending = wish.status === "pending";

  return (
    <div
      className={`border-l-[3px] rounded-r-md bg-surface-700 px-4 py-3 transition-colors ${
        priorityStyles[passenger.priority as 0 | 1 | 2] ?? priorityStyles[0]
      }`}
    >
      {/* Top row: passenger info + status */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          {/* Priority badge */}
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

          {/* Name + booking ref */}
          <button
            onClick={() => onViewProfile(passenger.id)}
            className="text-sm font-semibold text-text-primary hover:text-accent-blue transition-colors cursor-pointer"
          >
            {passenger.name}
          </button>
          <span className="font-mono text-xs text-text-muted">
            {passenger.bookingRef}
          </span>

          {/* Route summary */}
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
          {statusBadge[wish.status]}
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
        <div className="flex items-center gap-2 mb-3 ml-1">
          <span className="text-sm" role="img">
            {OPTION_TYPE_ICONS[selectedOption.type] ?? "•"}
          </span>
          <span className="text-sm text-text-primary">
            {selectedOption.summary}
          </span>
          {!selectedOption.available && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-amber/15 text-accent-amber">
              UNAVAILABLE
            </span>
          )}
        </div>
      )}

      {/* Denial reason (if denied) */}
      {wish.status === "denied" && wish.denialReason && (
        <div className="text-xs text-accent-red/80 ml-1 mb-2">
          Reason: {wish.denialReason}
        </div>
      )}

      {/* Confirmation details (if approved) */}
      {wish.status === "approved" && wish.confirmationDetails && (
        <div className="text-xs text-accent-green/80 ml-1 mb-2">
          {wish.confirmationDetails}
        </div>
      )}

      {/* Action buttons (only for pending) */}
      {isPending && (
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-surface-600/50">
          <button
            onClick={handleApprove}
            disabled={acting}
            className="px-6 py-3 text-sm font-bold rounded-md bg-accent-green text-surface-900 hover:brightness-110 hover:shadow-[0_0_12px_rgba(34,197,94,0.4)] active:scale-95 transition-all disabled:opacity-50 cursor-pointer"
          >
            {acting ? "..." : "APPROVE"}
          </button>

          {!showDenyInput ? (
            <button
              onClick={() => setShowDenyInput(true)}
              className="px-6 py-3 text-sm font-bold rounded-md bg-accent-red/20 text-accent-red border border-accent-red/30 hover:bg-accent-red hover:text-surface-900 hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] active:scale-95 transition-all cursor-pointer"
            >
              DENY
            </button>
          ) : (
            <div className="flex items-center gap-2 flex-1">
              <input
                type="text"
                value={denyReason}
                onChange={(e) => setDenyReason(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleDeny()}
                placeholder="Reason for denial..."
                autoFocus
                className="flex-1 px-3 py-3 text-sm rounded-md bg-surface-900 border border-accent-red/40 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-red"
              />
              <button
                onClick={handleDeny}
                disabled={acting || !denyReason.trim()}
                className="px-5 py-3 text-sm font-bold rounded-md bg-accent-red text-surface-900 hover:brightness-110 hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] active:scale-95 transition-all disabled:opacity-50 cursor-pointer"
              >
                CONFIRM DENY
              </button>
              <button
                onClick={() => {
                  setShowDenyInput(false);
                  setDenyReason("");
                }}
                className="px-3 py-3 text-sm text-text-muted hover:text-text-primary transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
