import { useState, useMemo, useEffect, useRef } from "react";
import { Layout } from "./components/Layout";
import { OverviewPanel } from "./components/OverviewPanel";
import { FlightOverview } from "./components/FlightOverview";
import { WishStream } from "./components/WishStream";
import { PassengerProfile } from "./components/PassengerProfile";
import { useDisruption } from "./hooks/use-disruption";
import { useWishes } from "./hooks/use-wishes";
import { api } from "./api";
import type { Disruption, Option, Wish, WSEvent } from "./types";

type Tab = "overview" | "wishes";

function isInputFocused() {
  const el = document.activeElement;
  return el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
}

function App() {
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  const [disruptionId, setDisruptionId] = useState<string | null>(null);
  const { disruption, passengers, loading, error } =
    useDisruption(disruptionId);
  const { wishes, pendingWishes, resolvedWishes, approve, deny, resolveManually } =
    useWishes(disruptionId);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [profileId, setProfileId] = useState<string | null>(null);
  const [optionsRaw, setOptionsRaw] = useState<Record<string, Option[]>>({});
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Refs for focusing search inputs in child components
  const paxSearchRef = useRef<HTMLInputElement>(null);
  const flightSearchRef = useRef<HTMLInputElement>(null);

  // Load all disruptions for the flight selector, auto-select first
  useEffect(() => {
    api.getDisruptions()
      .then((ds) => {
        setDisruptions(ds);
        if (!disruptionId && ds.length > 0) {
          setDisruptionId(ds[0].id);
        }
      })
      .catch((err) => {
        console.error("Failed to load disruptions:", err);
      });
  }, []);

  // Load options when disruption changes
  useEffect(() => {
    if (!disruptionId) return;
    api.getOptions(disruptionId).then(setOptionsRaw);
  }, [disruptionId]);

  // Handle disruption_created and options_updated WS events
  useEffect(() => {
    const unsub = api.onEvent((event: WSEvent) => {
      if (event.type === "disruption_created") {
        const { disruptionId: newId } = event.data as { disruptionId: string };
        api.getDisruption(newId).then((d) => {
          setDisruptions((prev) =>
            prev.some((existing) => existing.id === d.id)
              ? prev
              : [...prev, d]
          );
        });
      } else if (event.type === "options_updated" && disruptionId) {
        api.getOptions(disruptionId).then(setOptionsRaw);
      }
    });
    return unsub;
  }, [disruptionId]);

  // Global keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't intercept when typing in inputs
      if (isInputFocused()) {
        if (e.key === "Escape") {
          (document.activeElement as HTMLElement)?.blur();
          e.preventDefault();
        }
        return;
      }

      switch (e.key) {
        case "1":
          setActiveTab("overview");
          e.preventDefault();
          break;
        case "2":
          setActiveTab("wishes");
          e.preventDefault();
          break;
        case "/":
          e.preventDefault();
          paxSearchRef.current?.focus();
          break;
        case "f":
          e.preventDefault();
          flightSearchRef.current?.focus();
          break;
        case "Escape":
          if (profileId) {
            setProfileId(null);
            e.preventDefault();
          }
          break;
        case "?":
          setShowShortcuts((s) => !s);
          e.preventDefault();
          break;
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [profileId]);

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

  if (!disruptionId || loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full text-text-muted">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
            <span className="font-mono text-sm">
              {!disruptionId ? "Loading disruptions..." : "Connecting to operations..."}
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
            flightSearchRef={flightSearchRef}
          />
        </div>

        {/* Tab bar */}
        <div className="shrink-0 px-4 pt-4 flex items-center gap-1">
          <TabButton
            active={activeTab === "overview"}
            onClick={() => setActiveTab("overview")}
            shortcut="1"
          >
            Flight Overview
          </TabButton>
          <TabButton
            active={activeTab === "wishes"}
            onClick={() => setActiveTab("wishes")}
            count={pendingWishes.length}
            shortcut="2"
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
              searchRef={paxSearchRef}
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

      {/* Keyboard shortcuts bar */}
      {showShortcuts && (
        <div className="fixed bottom-0 left-0 right-0 bg-surface-800 border-t border-surface-600 px-5 py-2 flex items-center gap-6 z-50">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">Shortcuts</span>
          <Kbd k="1">Flight Overview</Kbd>
          <Kbd k="2">Wish Stream</Kbd>
          <Kbd k="/">Search passengers</Kbd>
          <Kbd k="F">Search flights</Kbd>
          <Kbd k="Esc">Close / clear</Kbd>
          <Kbd k="?">Toggle this bar</Kbd>
        </div>
      )}

      {/* Shortcut hint in corner */}
      {!showShortcuts && (
        <button
          onClick={() => setShowShortcuts(true)}
          className="fixed bottom-3 right-3 px-2 py-1 text-[10px] font-mono text-text-muted bg-surface-800 border border-surface-600 rounded hover:text-text-secondary hover:border-surface-500 transition-colors cursor-pointer z-50"
          title="Show keyboard shortcuts"
        >
          <span className="inline-block w-4 h-4 leading-4 text-center bg-surface-700 rounded text-[10px] mr-1">?</span>
          shortcuts
        </button>
      )}

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
  shortcut,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count?: number;
  shortcut?: string;
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
      {shortcut && (
        <kbd className="inline-block w-5 h-5 leading-5 text-center text-[10px] font-mono bg-surface-700 border border-surface-500 rounded text-text-muted mr-2">
          {shortcut}
        </kbd>
      )}
      {children}
      {count !== undefined && count > 0 && (
        <span className="ml-2 px-2 py-1 text-xs font-mono font-bold rounded-full bg-accent-blue text-surface-900 tabular-nums animate-pulse">
          {count}
        </span>
      )}
    </button>
  );
}

function Kbd({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-text-secondary">
      <kbd className="inline-block min-w-[20px] px-1.5 py-0.5 text-center text-[11px] font-mono font-bold bg-surface-700 border border-surface-500 rounded text-text-primary">
        {k}
      </kbd>
      <span className="text-text-muted">{children}</span>
    </span>
  );
}

export default App;
