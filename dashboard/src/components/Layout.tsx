import type { ReactNode } from "react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-900 flex flex-col">
      {/* Top bar */}
      <header className="h-12 bg-surface-800 border-b border-surface-600 flex items-center justify-between px-5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          <span className="font-mono text-sm font-semibold tracking-wider text-text-primary uppercase">
            Soft Landing
          </span>
          <span className="text-text-muted text-xs font-mono">
            Gate Agent Console
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-text-secondary">
          <span>MUC — Terminal 2</span>
          <span className="text-text-muted">|</span>
          <LiveClock />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}

function LiveClock() {
  return (
    <span className="tabular-nums" suppressHydrationWarning>
      {new Date().toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/Berlin",
      })}{" "}
      CET
    </span>
  );
}
