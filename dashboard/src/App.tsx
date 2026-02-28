import { useState, useMemo, useEffect } from "react";
import { Layout } from "./components/Layout";
import { OverviewPanel } from "./components/OverviewPanel";
import { FlightOverview } from "./components/FlightOverview";
import { WishStream } from "./components/WishStream";
import { PassengerProfile } from "./components/PassengerProfile";
import { useDisruption } from "./hooks/use-disruption";
import { useWishes } from "./hooks/use-wishes";
import { api } from "./api";
import type { Disruption, Option, Wish } from "./types";

type Tab = "overview" | "wishes";

function App() {
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  const [disruptionId, setDisruptionId] = useState<string>("dis-001");
  const { disruption, passengers, loading, error } =
    useDisruption(disruptionId);
  const { wishes, pendingWishes, resolvedWishes, approve, deny, resolveManually } =
    useWishes(disruptionId);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [profileId, setProfileId] = useState<string | null>(null);
  const [optionsRaw, setOptionsRaw] = useState<Record<string, Option[]>>({});

  // Load all disruptions for the flight selector
  useEffect(() => {
    api.getDisruptions().then(setDisruptions);
  }, []);

  // Load options when disruption changes
  useEffect(() => {
    api.getOptions(disruptionId).then(setOptionsRaw);
  }, [disruptionId]);

  // Build options map for wish cards and flight overview
  const optionsByPassenger = useMemo(() => {
    const map = new Map<string, Option[]>();
    for (const [paxId, opts] of Object.entries(optionsRaw)) {
      map.set(paxId, opts);
    }
    return map;
  }, [optionsRaw]);

  // Build latest wish per passenger (for flight overview)
  const wishesByPassenger = useMemo(() => {
    const map = new Map<string, Wish>();
    // Process in order so later wishes overwrite earlier ones
    for (const wish of wishes) {
      map.set(wish.passengerId, wish);
    }
    return map;
  }, [wishes]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full text-text-muted">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
            <span className="font-mono text-sm">
              Connecting to operations...
            </span>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !disruption) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full text-accent-red">
          <span className="font-mono text-sm">
            Error: {error ?? "Failed to load disruption"}
          </span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col h-[calc(100vh-48px)]">
        {/* Overview panel */}
        <div className="shrink-0 p-4 pb-0">
          <OverviewPanel
            disruption={disruption}
            passengers={passengers}
            pendingWishes={pendingWishes}
            disruptions={disruptions}
            onSelectDisruption={setDisruptionId}
          />
        </div>

        {/* Tab bar */}
        <div className="shrink-0 px-4 pt-4 flex items-center gap-1">
          <TabButton
            active={activeTab === "overview"}
            onClick={() => setActiveTab("overview")}
          >
            Flight Overview
          </TabButton>
          <TabButton
            active={activeTab === "wishes"}
            onClick={() => setActiveTab("wishes")}
            count={pendingWishes.length}
          >
            Wish Stream
          </TabButton>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden m-4 mt-2 bg-surface-800 border border-surface-600 rounded-lg">
          {activeTab === "overview" ? (
            <FlightOverview
              disruption={disruption}
              passengers={passengers}
              optionsByPassenger={optionsByPassenger}
              wishesByPassenger={wishesByPassenger}
              onViewProfile={setProfileId}
              onResolve={resolveManually}
            />
          ) : (
            <WishStream
              pendingWishes={pendingWishes}
              resolvedWishes={resolvedWishes}
              passengers={passengers}
              optionsByPassenger={optionsByPassenger}
              onApprove={approve}
              onDeny={deny}
              onViewProfile={setProfileId}
            />
          )}
        </div>
      </div>

      {/* Passenger profile modal */}
      {profileId && (
        <PassengerProfile
          passengerId={profileId}
          onClose={() => setProfileId(null)}
        />
      )}
    </Layout>
  );
}

function TabButton({
  active,
  onClick,
  count,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 text-base font-bold rounded-t-lg transition-all cursor-pointer ${
        active
          ? "bg-surface-800 text-text-primary border-2 border-surface-500 border-b-surface-800"
          : "text-text-muted hover:text-text-secondary hover:bg-surface-800/50 border-2 border-transparent"
      }`}
    >
      {children}
      {count !== undefined && count > 0 && (
        <span className="ml-2 px-2 py-1 text-xs font-mono font-bold rounded-full bg-accent-blue text-surface-900 tabular-nums animate-pulse">
          {count}
        </span>
      )}
    </button>
  );
}

export default App;
