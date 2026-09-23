const pillars = [
  {
    icon: (
      <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M3 7V5a2 2 0 012-2h2m10 0h2a2 2 0 012 2v2m0 10v2a2 2 0 01-2 2h-2m-10 0H5a2 2 0 01-2-2v-2" strokeLinecap="round" strokeLinejoin="round"></path>
        <circle cx="12" cy="12" r="3"></circle>
      </svg>
    ),
    title: '1. Upload or Paste',
    description: 'Snap a photo of any gazette paper, court summons, pension notification, or paste raw text.',
  },
  {
    icon: (
      <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: '2. Actionable Checklist',
    description: 'Get key deadlines, necessary documents, fees, and eligibility broken down into three punchy bullet points.',
  },
  {
    icon: (
      <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
        <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
    title: '3. Clear Audio Readout',
    description: 'Listen in your preferred mother tongue at a comfortable speed, designed specifically for first-time digital citizens.',
  },
];

export default function CorePillars() {
  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-10 reveal-section">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {pillars.map((pillar, index) => (
          <div key={pillar.title} className="bg-white stroke-border rounded-3xl p-7 card-shadow flex flex-col justify-between group">
            <div>
              <div className={`w-12 h-12 rounded-xl bg-[#F9C915] stroke-border flex items-center justify-center mb-6 transition-transform ${index === 0 ? 'group-hover:rotate-6 group-hover:scale-110' : index === 1 ? 'group-hover:-rotate-6 group-hover:scale-110' : 'group-hover:rotate-6 group-hover:scale-110'}`}>
                {pillar.icon}
              </div>
              <h3 className="text-xl font-extrabold mb-2.5 tracking-tight group-hover:translate-x-1 transition-transform">{pillar.title}</h3>
              <p className="text-sm font-medium text-neutral-700 leading-relaxed">{pillar.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
