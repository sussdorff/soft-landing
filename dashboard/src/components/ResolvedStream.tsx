import type { Wish, Passenger, Option } from "../types";
import { ResolvedCard } from "./ResolvedCard";

interface Props {
  resolvedWishes: Wish[];
  passengers: Passenger[];
  optionsByPassenger: Map<string, Option[]>;
  onViewProfile: (passengerId: string) => void;
  onResolve: (passengerId: string, optionId: string) => Promise<void>;
  onRefreshOptions: (passengerId: string) => Promise<Option[]>;
}

export function ResolvedStream({
  resolvedWishes,
  passengers,
  optionsByPassenger,
  onViewProfile,
  onResolve,
  onRefreshOptions,
}: Props) {
  const paxMap = new Map(passengers.map((p) => [p.id, p]));

  function getSelectedOption(wish: Wish): Option | undefined {
    const opts = optionsByPassenger.get(wish.passengerId);
    return opts?.find((o) => o.id === wish.selectedOptionId);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-600">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-text-primary">
            Resolved Passengers
          </h2>
          {resolvedWishes.length > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-surface-500 text-text-secondary tabular-nums">
              {resolvedWishes.length}
            </span>
          )}
        </div>
      </div>

      {/* Resolved list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
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
      </div>
    </div>
  );
}
