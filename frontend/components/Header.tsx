export default function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-command-border bg-command-surface px-6">
      <div>
        <h2 className="text-sm font-semibold text-command-text">
          Real-Time Moderation Engine
        </h2>
        <p className="text-xs text-command-muted">
          Live toxicity monitoring and cluster visualization
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-command-accent animate-pulse" />
        <span className="text-xs font-medium uppercase tracking-wide text-command-muted">
          Standby
        </span>
      </div>
    </header>
  );
}
