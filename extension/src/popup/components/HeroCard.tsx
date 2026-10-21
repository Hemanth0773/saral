export default function HeroCard() {
  return (
    <section className="brutal-card relative overflow-hidden bg-white p-4">
      <div className="mb-1 flex items-center justify-between gap-1.5">
        <span className="brutal-pill-sm inline-flex items-center gap-1.5 bg-white px-2 py-0.5">
          <span className="h-2 w-2 rounded-full bg-saral-ink" aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-saral-ink">
            Browser Copilot
          </span>
        </span>
        <span className="rounded-full bg-saral-paleYellow px-2 py-0.5 text-[10px] font-bold text-saral-ink">
          v2.4 Live
        </span>
      </div>

      <h1 className="text-xl font-extrabold tracking-tight text-saral-ink">Make it simple.</h1>
      <p className="mt-0.5 text-[12px] font-medium leading-snug text-saral-ink/75">
        Upload a civic notice, paste dense policy text, or drop any official URL.
      </p>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-6 -right-6 h-20 w-20 rounded-full bg-black/5"
      />
    </section>
  );
}
