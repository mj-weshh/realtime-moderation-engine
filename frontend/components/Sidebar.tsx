export default function Sidebar() {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-command-border bg-command-surface">
      <div className="border-b border-command-border px-4 py-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-command-accent">
          Moderation
        </p>
        <h1 className="mt-1 text-sm font-bold text-command-text">
          Command Center
        </h1>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        <span className="rounded-md border border-command-accent/40 bg-command-accent/10 px-3 py-2 text-sm font-medium text-command-accent">
          Dashboard
        </span>
        <span className="rounded-md px-3 py-2 text-sm text-command-muted">
          Alerts
        </span>
        <span className="rounded-md px-3 py-2 text-sm text-command-muted">
          Network Graph
        </span>
        <span className="rounded-md px-3 py-2 text-sm text-command-muted">
          Settings
        </span>
      </nav>
    </aside>
  );
}
