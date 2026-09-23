export default function Footer() {
  return (
    <footer className="w-full max-w-7xl mx-auto px-6 lg:px-12 py-10 flex flex-col sm:flex-row items-center justify-between gap-4 border-t-2 border-black/15 text-xs font-bold">
      <div className="flex items-center gap-1.5">
        <span className="text-base font-extrabold">Saral</span>
        <span className="w-2 h-2 rounded-full bg-black inline-block"></span>
        <span className="text-neutral-800 ml-2">© 2024 Saral. Simple, bright, accessible.</span>
      </div>
      <div className="flex items-center gap-6">
        <a className="hover:underline transition-all underline-offset-4" href="#top">Privacy</a>
        <a className="hover:underline transition-all underline-offset-4" href="#top">Terms</a>
        <a className="hover:underline transition-all underline-offset-4" href="#top">Accessibility</a>
      </div>
    </footer>
  );
}
