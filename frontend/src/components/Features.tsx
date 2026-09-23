const features = [
  {
    number: '01',
    title: 'AI Simplification',
    description: 'Turns dense, multi-clause government decrees into short, unambiguous sentences anyone can digest.',
  },
  {
    number: '02',
    badge: 'Real-time Metrics',
    title: 'Readability Analysis',
    description: 'Calculates precise Flesch-Kincaid grade levels before and after, making readability gains quantitatively visible.',
  },
  {
    number: '03',
    title: 'Important Information',
    description: 'Extracts hard facts: eligibility conditions, filing deadlines, required certificates, benefits, and sanction amounts.',
  },
  {
    number: '04',
    badge: 'Kannada & English',
    title: 'Translation',
    description: 'Translate simplified policies into supported regional languages without losing civic context or legal intent.',
  },
  {
    number: '05',
    badge: '12 Voices',
    title: 'Text to Speech',
    description: 'Listen to synthesized plain-language summaries on mobile. Perfect for auditory learners or on-the-go comprehension.',
    dark: true,
  },
  {
    number: '06',
    badge: '100% Grounded',
    title: 'Source Validation',
    description: 'Every simplified claim is cross-checked against source gazette text to prevent hallucinations or altered mandates.',
  },
];

export default function Features() {
  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section">
      <div className="mb-10">
        <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-3">Everything you need to understand the fine print.</h2>
        <p className="text-neutral-900 font-medium text-lg max-w-2xl">Engineered specifically to deconstruct bureaucratic complexity.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <div key={feature.number} className={`${feature.dark ? 'bg-black text-white' : 'bg-white'} stroke-border rounded-3xl p-7 card-shadow flex flex-col justify-between group`}>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-mono font-black ${feature.dark ? 'text-neutral-500 group-hover:text-neutral-300' : 'text-neutral-400 group-hover:text-black'} transition-colors`}>{feature.number}</span>
                {feature.badge && <span className={`${feature.dark ? 'bg-[#F9C915] text-black' : 'bg-[#FEF9C3] text-black group-hover:bg-[#F9C915]'} text-xs font-extrabold px-2.5 py-0.5 rounded-full stroke-border-thin transition-colors`}>{feature.badge}</span>}
              </div>
              <h3 className={`text-xl font-extrabold mt-2 mb-3 ${feature.dark ? 'text-white' : ''}`}>{feature.title}</h3>
              <p className={`text-sm font-medium leading-relaxed ${feature.dark ? 'text-neutral-300' : 'text-neutral-700'}`}>{feature.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
