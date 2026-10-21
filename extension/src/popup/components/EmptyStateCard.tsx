type EmptyStateCardProps = {
  isReading: boolean;
};
export default function EmptyStateCard({ isReading }: EmptyStateCardProps) {
  return (
    <section className="brutal-card bg-white p-3">
      <div className="mb-2 flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-full bg-saral-outline shadow-[1px_1px_0_0_#0D0D0D]"
          aria-hidden="true"
        />
        <h2 className="text-[12px] font-extrabold uppercase tracking-wider text-saral-ink">
          Instant Summary
        </h2>
      </div>

      {isReading ? (
        <p className="text-[12px] font-semibold text-saral-ink/70">
          Reading the page… Saral is collecting the text so you can review it before anything is
          sent.
        </p>
      ) : (
        <>
          <p className="text-[12px] font-semibold text-saral-ink/70">
            Nothing simplified yet. Read the page you are on, attach a notice, or paste a circular
            — then press Simplify.
          </p>
          <p className="mt-1.5 text-[10px] font-semibold text-saral-ink/45">
            Saral only sends content after you review it.
          </p>
        </>
      )}
    </section>
  );
}
