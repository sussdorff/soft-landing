import type { Passenger } from "../types";

interface Props {
  passengers: Passenger[];
  onViewProfile: (passengerId: string) => void;
}

export function PassengerList({ passengers, onViewProfile }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-600">
        <h2 className="text-sm font-semibold text-text-primary">
          All Passengers
        </h2>
        <span className="text-[10px] font-mono text-text-muted tabular-nums">
          {passengers.length} total
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface-800">
            <tr className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">PNR</th>
              <th className="text-left px-4 py-2 font-medium">Route</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-right px-4 py-2 font-medium">Priority</th>
            </tr>
          </thead>
          <tbody>
            {passengers.map((pax) => (
              <tr
                key={pax.id}
                onClick={() => onViewProfile(pax.id)}
                className={`border-t border-surface-700 hover:bg-surface-700/50 cursor-pointer transition-colors ${
                  pax.priority >= 2
                    ? "bg-priority-critical/20"
                    : pax.priority === 1
                    ? "bg-priority-elevated/20"
                    : ""
                }`}
              >
                <td className="px-4 py-2 text-text-primary font-medium">
                  {pax.name}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-text-secondary">
                  {pax.bookingRef}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-text-secondary">
                  {pax.originalItinerary.segments
                    .map((s) => s.origin)
                    .concat(
                      pax.originalItinerary.segments[
                        pax.originalItinerary.segments.length - 1
                      ]?.destination ?? ""
                    )
                    .join(" → ")}
                </td>
                <td className="px-4 py-2">
                  <StatusPill status={pax.status} />
                </td>
                <td className="px-4 py-2 text-right">
                  {pax.denialCount > 0 && (
                    <span className="font-mono text-xs text-accent-red">
                      {pax.denialCount}x
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    unaffected: "bg-surface-600 text-text-muted",
    notified: "bg-accent-blue/15 text-accent-blue",
    chose: "bg-accent-purple/15 text-accent-purple",
    approved: "bg-accent-green/15 text-accent-green",
    denied: "bg-accent-red/15 text-accent-red",
  };

  return (
    <span
      className={`inline-block px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase tracking-wider ${
        styles[status] ?? styles.unaffected
      }`}
    >
      {status}
    </span>
  );
}
