type HeroSectionProps = {
  onSelectSample: (url: string, tabIndex: number) => void;
};

const samples = [
  { title: 'Gazette Notification 412-A', url: 'https://egazette.gov.in/notification/412-A-ration-allotment.pdf', icon: '📜', tabIndex: 0 },
  { title: 'PM-Kisan Circular', url: 'https://pmkisan.gov.in/circulars/eKYC-mandate-v4.pdf', icon: '🌾', tabIndex: 1 },
  { title: 'Property Registry Rule', url: 'https://dor.gov.in/notifications/property-registration-amendment.pdf', icon: '🏡', tabIndex: 2 },
];

export default function HeroSection({ onSelectSample }: HeroSectionProps) {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 pt-6 pb-16 lg:py-12" id="top">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
        <div className="lg:col-span-7 min-w-0 flex flex-col items-start">
          <h1 className="text-5xl sm:text-6xl xl:text-7xl font-extrabold tracking-tight leading-[1.05] mb-6">
            Government<br />information,<br />made simple.
          </h1>
          <p className="text-base sm:text-lg xl:text-xl font-medium text-neutral-900 max-w-full sm:max-w-xl leading-relaxed mb-8">
            Understand complex government gazettes, citizen schemes, and legal circulars without the jargon. Transformed instantly into crystal-clear plain text & spoken audio.
          </p>
          <div className="flex flex-wrap items-center gap-4 mb-8">
            <a className="btn-tactile bg-black hover:bg-neutral-900 text-white font-bold px-7 py-3.5 rounded-full stroke-border flex items-center gap-2 group" href="#try-saral">
              <span>Simplify a Document</span>
              <span className="text-base group-hover:translate-x-1.5 transition-transform duration-200">→</span>
            </a>
            <button
              className="btn-tactile bg-white hover:bg-neutral-50 text-black font-bold px-6 py-3.5 rounded-full stroke-border flex items-center gap-2.5 cursor-pointer"
              onClick={() => scrollToSection('audio-playback')}
              type="button"
            >
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8 5v14l11-7z"></path>
              </svg>
              <span>Audio Playback</span>
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 mb-8 text-xs font-bold">
            <span className="text-xs font-extrabold uppercase tracking-wider mr-1 text-black/90">TRY SAMPLE:</span>
            {samples.map((sample) => (
              <button
                key={sample.title}
                className="sample-tag-btn bg-[#FEF9C3] hover:bg-white stroke-border-thin px-3 py-1.5 rounded-full flex items-center gap-1.5 transition-all hover:-translate-y-0.5 active:translate-y-0 cursor-pointer shadow-sm"
                onClick={() => onSelectSample(sample.url, sample.tabIndex)}
                type="button"
              >
                <span className="transition-transform group-hover:scale-125">{sample.icon}</span>
                <span>{sample.title}</span>
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs font-bold">
            <div className="bg-white stroke-border px-3.5 py-1.5 rounded-full flex items-center gap-2 hover:bg-neutral-50 transition-transform hover:-translate-y-0.5 cursor-default">
              <span className="w-2 h-2 rounded-full bg-black animate-ping"></span>
              <span>Instant Readability Metric</span>
            </div>
            <div className="bg-white stroke-border px-3.5 py-1.5 rounded-full flex items-center gap-2 hover:bg-neutral-50 transition-transform hover:-translate-y-0.5 cursor-default">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
              <span>Voice TTS Engine</span>
            </div>
            <div className="bg-white stroke-border px-3.5 py-1.5 rounded-full flex items-center gap-2 hover:bg-neutral-50 transition-transform hover:-translate-y-0.5 cursor-default">
              <span className="font-mono font-bold">文A</span>
              <span>12 Regional Languages</span>
            </div>
          </div>
        </div>
        <div className="lg:col-span-5 min-w-0 relative flex justify-center lg:justify-end">
          <div className="relative w-full max-w-lg">
            <div className="absolute -top-4 left-2 sm:left-6 z-20 bg-white stroke-border px-3.5 py-1.5 rounded-full flex items-center gap-2 card-shadow-sm animate-float-1 select-none">
              <span className="text-xs font-black text-neutral-500">12.4</span>
              <span className="text-xs font-bold text-neutral-400">→</span>
              <span className="bg-[#F9C915] text-xs font-black px-2 py-0.5 rounded-full stroke-border-thin transition-transform inline-block">5.0</span>
              <span className="text-xs font-bold">Grade Level</span>
            </div>
            <div className="absolute -top-3 right-2 sm:right-4 z-20 bg-black text-white stroke-border px-3.5 py-1.5 rounded-full flex items-center gap-1.5 text-xs font-bold card-shadow-sm animate-float-2 select-none">
              <span className="text-sm">🛡</span>
              <span className="font-extrabold">100% Fact Preserved</span>
            </div>
            <div className="w-full bg-white stroke-border rounded-3xl p-4 sm:p-6 relative card-shadow-lg overflow-hidden group">
              <div className="w-full rounded-2xl overflow-hidden stroke-border bg-white flex items-center justify-center p-2 group-hover:scale-[1.01] transition-transform duration-300">
                <img alt="Saral document simplification illustration" className="w-full h-full object-contain select-none block" src="/hero-illustration.svg" />
              </div>
              <div className="mt-4 flex justify-end">
                <button aria-label="Go to audio playback" className="btn-tactile inline-flex items-center gap-3 bg-white stroke-border px-4 py-2 rounded-full cursor-pointer text-left transition-transform active:scale-95" onClick={() => scrollToSection('audio-playback')} type="button">
                  <span className="w-7 h-7 rounded-full bg-black text-white flex items-center justify-center transition-colors">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path d="M15.536 8.464a5 5 0 010 7.072M12 6v12m-3-9H5a1 1 0 00-1 1v4a1 1 0 001 1h4l4 4V4l-4 4z" strokeLinecap="round" strokeLinejoin="round"></path>
                    </svg>
                  </span>
                  <div className="text-left">
                    <p className="text-xs font-extrabold leading-none">Clear Audio Readout</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="flex items-center gap-0.5 h-3 text-neutral-600" aria-hidden="true">
                        <span className="eq-bar !w-[2px] !h-[4px]"></span>
                        <span className="eq-bar !w-[2px] !h-[8px]"></span>
                        <span className="eq-bar !w-[2px] !h-[12px]"></span>
                        <span className="eq-bar !w-[2px] !h-[6px]"></span>
                        <span className="eq-bar !w-[2px] !h-[4px]"></span>
                      </div>
                      <p className="text-[11px] font-semibold text-neutral-600 tracking-wider ml-1">0:45 min</p>
                    </div>
                  </div>
                </button>
              </div>
            </div>
            <div aria-hidden="true" className="absolute -bottom-6 right-6 grid grid-cols-3 gap-1.5 opacity-60 pointer-events-none">
              {Array.from({ length: 6 }).map((_, index) => <span key={index} className="w-1.5 h-1.5 rounded-full bg-black"></span>)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}