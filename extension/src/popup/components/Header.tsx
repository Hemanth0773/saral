import { UserIcon } from './Icons';

type HeaderProps = {
  onOpenSettings: () => void;
};

export default function Header({ onOpenSettings }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-black/10 bg-saral-surface/95 backdrop-blur">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-1.5">
          <span className="select-none text-lg font-extrabold tracking-tight text-saral-ink">
            Saral
          </span>
          <span className="inline-block h-2 w-2 rounded-full bg-saral-yellow" aria-hidden="true" />
          <span className="sr-only">Browser Copilot</span>
        </div>
        <button
          type="button"
          onClick={onOpenSettings}
          aria-label="Saral settings: backend address and help"
          className="focus-ring flex min-h-[44px] min-w-[44px] items-center justify-end rounded-full"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-saral-ink text-white">
            <UserIcon className="text-[18px]" />
          </span>
        </button>
      </div>
    </header>
  );
}
