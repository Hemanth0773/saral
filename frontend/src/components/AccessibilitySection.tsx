const accessibilityCards = [
  {
    number: '01',
    title: 'Visual Clarity',
    description: 'Clear visual hierarchy, uncluttered typography, and ample spacing to prevent reader overwhelm.',
  },
  {
    number: '02',
    title: 'Cognitive Accessibility',
    description: 'Dismantles bureaucratic jargon and nested conditionals to drastically lower mental load.',
  },
  {
    number: '03',
    title: 'Language Accessibility',
    description: 'Regional translation capabilities ensure local communities read directives in their native tongue.',
  },
  {
    number: '04',
    title: 'Audio Accessibility',
    description: 'High-fidelity speech synthesis allows non-readers to listen to full simplifications effortlessly.',
  },
];

export default function AccessibilitySection() {
  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section">
      <div className="bg-black text-white stroke-border rounded-3xl p-8 sm:p-12 card-shadow-lg">
        <div className="max-w-3xl mb-10">
          <div className="inline-block bg-[#F9C915] text-black stroke-border px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-4">↑ UNIVERSAL DESIGN</div>
          <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">Designed for everyone.</h2>
          <p className="text-neutral-300 font-medium text-lg leading-relaxed">Government information should be understandable regardless of reading ability, language, or preferred way of consuming information.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {accessibilityCards.map((card) => (
            <div key={card.number} className="bg-[#171717] stroke-border-thin border-neutral-700 hover:border-[#F9C915] rounded-2xl p-6 flex flex-col justify-between transition-all duration-200 hover:-translate-y-1">
              <div>
                <span className="text-xs font-mono font-bold text-[#F9C915] uppercase tracking-wider">{card.number}</span>
                <h3 className="text-lg font-extrabold text-white mt-2 mb-2">{card.title}</h3>
                <p className="text-xs sm:text-sm text-neutral-400 font-medium leading-relaxed">{card.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
