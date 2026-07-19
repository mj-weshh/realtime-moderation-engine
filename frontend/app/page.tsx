import LiveFeed from "@/components/LiveFeed";

export default function Home() {
  return (
    <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[320px_1fr]">
      <section className="flex min-h-0 flex-col border-b border-command-border lg:border-b-0 lg:border-r">
        <div className="border-b border-command-border px-4 py-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-command-accent-muted">
            Live Alert Feed
          </h3>
        </div>
        <LiveFeed />
      </section>

      <section className="flex min-h-0 flex-col">
        <div className="border-b border-command-border px-4 py-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-command-accent">
            Network Graph
          </h3>
        </div>
        <div className="flex flex-1 items-center justify-center p-6">
          <p className="text-center text-sm text-command-muted">
            Network Graph — visualization in Day 15
          </p>
        </div>
      </section>
    </div>
  );
}
