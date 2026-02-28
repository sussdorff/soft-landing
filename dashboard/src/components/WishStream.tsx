import type { Wish, Passenger, Option } from "../types";
import { WishCard } from "./WishCard";

interface Props {
  pendingWishes: Wish[];
  resolvedWishes: Wish[];
  passengers: Passenger[];
  optionsByPassenger: Map<string, Option[]>;
  onApprove: (wishId: string) => void;
  onDeny: (wishId: string, reason: string) => void;
  onViewProfile: (passengerId: string) => void;
}

export function WishStream({
  pendingWishes,
  resolvedWishes,
  passengers,
  optionsByPassenger,
  onApprove,
  onDeny,
  onViewProfile,
}: Props) {
  const paxMap = new Map(passengers.map((p) => [p.id, p]));

  function getSelectedOption(wish: Wish): Option | undefined {
    const opts = optionsByPassenger.get(wish.passengerId);
    return opts?.find((o) => o.id === wish.selectedOptionId);
  }

  // Sort pending wishes: highest priority first, then earliest submission
  const sortedPending = [...pendingWishes].sort((a, b) => {
    const aPax = paxMap.get(a.passengerId);
    const bPax = paxMap.get(b.passengerId);
    const aPri = aPax?.priority ?? 0;
    const bPri = bPax?.priority ?? 0;
    if (aPri !== bPri) return bPri - aPri;
    return a.submittedAt.localeCompare(b.submittedAt);
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-600">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-text-primary">
            Passenger Wishes
          </h2>
          {pendingWishes.length > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-accent-blue/20 text-accent-blue tabular-nums">
              {pendingWishes.length}
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
          Live Stream
        </span>
      </div>

      {/* Wish list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {/* Pending section */}
        {sortedPending.length > 0 && (
          <>
            <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider mb-2">
              Pending ({sortedPending.length})
            </div>
            {sortedPending.map((wish) => (
              <WishCard
                key={wish.id}
                wish={wish}
                passenger={paxMap.get(wish.passengerId)}
                selectedOption={getSelectedOption(wish)}
                onApprove={onApprove}
                onDeny={onDeny}
                onViewProfile={onViewProfile}
              />
            ))}
          </>
        )}

        {/* Resolved section */}
        {resolvedWishes.length > 0 && (
          <>
            <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider mt-4 mb-2">
              Resolved ({resolvedWishes.length})
            </div>
            {resolvedWishes.map((wish) => (
              <WishCard
                key={wish.id}
                wish={wish}
                passenger={paxMap.get(wish.passengerId)}
                selectedOption={getSelectedOption(wish)}
                onApprove={onApprove}
                onDeny={onDeny}
                onViewProfile={onViewProfile}
              />
            ))}
          </>
        )}

        {pendingWishes.length === 0 && resolvedWishes.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-text-muted text-sm">
            <div className="text-2xl mb-2">—</div>
            No wishes submitted yet
          </div>
        )}
      </div>
    </div>
  );
}
