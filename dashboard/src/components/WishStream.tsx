import { useState } from "react";
import type { Wish, Passenger, Option } from "../types";
import { WishCard } from "./WishCard";
import { ResolvedCard } from "./ResolvedCard";

type SubTab = "incoming" | "resolved";

interface Props {
  pendingWishes: Wish[];
  resolvedWishes: Wish[];
  passengers: Passenger[];
  optionsByPassenger: Map<string, Option[]>;
  onApprove: (wishId: string) => void;
  onDeny: (wishId: string, reason: string) => void;
  onViewProfile: (passengerId: string) => void;
  onResolve: (passengerId: string, optionId: string) => Promise<void>;
  onRefreshOptions: (passengerId: string) => Promise<Option[]>;
}

export function WishStream({
  pendingWishes,
  resolvedWishes,
  passengers,
  optionsByPassenger,
  onApprove,
  onDeny,
  onViewProfile,
  onResolve,
  onRefreshOptions,
}: Props) {
  const [subTab, setSubTab] = useState<SubTab>("incoming");
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
      {/* Header with sub-tabs */}
      <div className="px-5 py-3 border-b border-surface-600">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-primary">
            Passenger Wishes
          </h2>
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
            Live Stream
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setSubTab("incoming")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              subTab === "incoming"
                ? "bg-surface-600 text-text-primary"
                : "text-text-muted hover:text-text-secondary hover:bg-surface-700"
            }`}
          >
            Incoming
            {pendingWishes.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-accent-blue/20 text-accent-blue tabular-nums">
                {pendingWishes.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setSubTab("resolved")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
              subTab === "resolved"
                ? "bg-surface-600 text-text-primary"
                : "text-text-muted hover:text-text-secondary hover:bg-surface-700"
            }`}
          >
            Resolved
            {resolvedWishes.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-surface-500 text-text-secondary tabular-nums">
                {resolvedWishes.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {subTab === "incoming" && (
          <>
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
            {sortedPending.length === 0 && (
              <div className="flex flex-col items-center justify-center h-40 text-text-muted text-sm">
                <div className="text-2xl mb-2">—</div>
                No pending wishes
              </div>
            )}
          </>
        )}

        {subTab === "resolved" && (
          <>
            {resolvedWishes.map((wish) => (
              <ResolvedCard
                key={wish.id}
                wish={wish}
                passenger={paxMap.get(wish.passengerId)}
                selectedOption={getSelectedOption(wish)}
                allOptions={optionsByPassenger.get(wish.passengerId) ?? []}
                onViewProfile={onViewProfile}
                onResolve={onResolve}
                onRefreshOptions={onRefreshOptions}
              />
            ))}
            {resolvedWishes.length === 0 && (
              <div className="flex flex-col items-center justify-center h-40 text-text-muted text-sm">
                <div className="text-2xl mb-2">—</div>
                No resolved passengers yet
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
