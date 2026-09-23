const steps = [
  {
    number: '01',
    icon: (
      <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: 'Upload a government document.',
    description: 'Take a picture, upload a PDF, or paste an official gazette link directly into the secure processing pipeline.',
  },
  {
    number: '02',
    icon: (
      <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M13 10V3L4 14h7v7l9-11h-7z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: 'Complex language is rewritten.',
    description: 'Our civic language model replaces labyrinthine clauses with direct, active voice at a 6th-grade level.',
  },
  {
    number: '03',
    icon: (
      <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: 'Important information is extracted.',
    description: 'Instantly surface eligibility criteria, application deadlines, required paperwork, and exact benefit sums.',
  },
  {
    number: '04',
    icon: (
      <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M15.536 8.464a5 5 0 010 7.072M12 6v12m-3-9H5a1 1 0 00-1 1v4a1 1 0 001 1h4l4 4V4l-4 4z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: 'Read or listen in your language.',
    description: 'Access clear local translations and natural synthesized audio so comprehension has zero literacy friction.',
  },
];

export default function HowSaralWorks() {
  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section" id="how-it-works">
      <div className="mb-10">
        <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-3">How Saral works</h2>
        <p className="text-neutral-900 font-medium text-lg max-w-2xl">A streamlined 4-step transformation from legal jargon to practical clarity.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {steps.map((step) => (
          <div key={step.number} className="bg-white stroke-border rounded-3xl p-6 card-shadow flex flex-col justify-between group">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-neutral-100 stroke-border-thin group-hover:bg-[#F9C915] transition-colors">{step.number}</span>
                <div className="w-10 h-10 rounded-xl bg-[#F9C915] stroke-border flex items-center justify-center group-hover:scale-110 transition-transform">{step.icon}</div>
              </div>
              <h3 className="text-lg font-extrabold mb-2 leading-snug">{step.title}</h3>
              <p className="text-xs sm:text-sm font-medium text-neutral-700 leading-relaxed">{step.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
