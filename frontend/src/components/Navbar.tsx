type NavbarProps = {
  ttsPlaying: boolean;
  ttsLoading: boolean;
  onToggleTts: () => void;
};

export default function Navbar({ ttsPlaying, ttsLoading, onToggleTts }: NavbarProps) {
  return (
    <header className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-5 sm:py-6 flex items-center justify-between">
      <a aria-label="Saral Home" className="group flex shrink-0 items-center gap-1 text-2xl font-extrabold tracking-tight transition-transform duration-200 active:scale-95" href="#top">
        <span className="group-hover:tracking-normal transition-all">Saral</span>
        <span className="w-2.5 h-2.5 rounded-full bg-black inline-block ml-0.5 group-hover:scale-125 transition-transform"></span>
      </a>
      <nav aria-label="Main Navigation" className="flex shrink-0 items-center gap-2 sm:gap-4 lg:gap-6">
        <a className="hidden md:inline-block text-sm font-bold hover:underline transition-all underline-offset-4 decoration-2" href="#how-it-works">How It Works</a>
        <button
          aria-label="Text to speech quick demo"
          aria-pressed={ttsPlaying}
          className="btn-tactile bg-white hover:bg-neutral-100 text-xs font-bold px-2.5 sm:px-3.5 py-2 rounded-full stroke-border flex shrink-0 items-center gap-1.5 cursor-pointer disabled:opacity-70 disabled:cursor-wait"
          disabled={ttsLoading}
          onClick={onToggleTts}
          type="button"
        >
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
            <path d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" strokeLinecap="round" strokeLinejoin="round"></path>
          </svg>
          <span className="shrink-0">{ttsLoading ? 'Connecting...' : 'TTS'}</span>
          <span className={`${ttsPlaying ? 'flex' : 'hidden'} shrink-0 items-end gap-0.5 h-3 ml-0.5 eq-playing`} aria-hidden="true">
            <span className="w-0.5 h-2 bg-black rounded-full"></span>
            <span className="w-0.5 h-3 bg-black rounded-full"></span>
            <span className="w-0.5 h-1.5 bg-black rounded-full"></span>
          </span>
        </button>
        <a className="btn-tactile bg-black text-white hover:bg-neutral-900 text-xs sm:text-sm font-bold px-4 sm:px-6 py-2 sm:py-2.5 rounded-full stroke-border shrink-0 inline-block" href="#try-saral">
          Get Started
        </a>
        <button aria-label="User Profile" className="w-9 h-9 sm:w-10 sm:h-10 shrink-0 rounded-full stroke-border bg-white flex items-center justify-center hover:bg-neutral-100 transition-colors btn-tactile cursor-pointer" type="button">
          <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" strokeLinecap="round" strokeLinejoin="round"></path>
          </svg>
        </button>
      </nav>
    </header>
  );
}
