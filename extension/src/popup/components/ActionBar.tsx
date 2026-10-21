import { BoltIcon, SpinnerIcon, TranslateIcon, VolumeIcon } from './Icons';

type ActionBarProps = {
  onSimplify: () => void;
  onTranslate: () => void;
  onReadAloud: () => void;
  isSimplifying: boolean;
  isTranslating: boolean;
  isTtsLoading: boolean;
  canSimplify: boolean;
  canTranslate: boolean;
  canReadAloud: boolean;
};

const baseButton =
  'btn-tactile flex w-full items-center justify-center gap-1.5 rounded-full px-2 py-2.5 text-[12px] font-extrabold disabled:opacity-45';

export default function ActionBar({
  onSimplify,
  onTranslate,
  onReadAloud,
  isSimplifying,
  isTranslating,
  isTtsLoading,
  canSimplify,
  canTranslate,
  canReadAloud,
}: ActionBarProps) {
  return (
    <section className="grid grid-cols-3 gap-2" aria-label="Saral actions">
      <button
        type="button"
        onClick={onSimplify}
        disabled={!canSimplify || isSimplifying}
        aria-busy={isSimplifying}
        className={`${baseButton} border-2 border-saral-ink bg-saral-ink text-white shadow-[3px_3px_0_0_#735C00]`}
      >
        {isSimplifying ? (
          <SpinnerIcon className="text-[16px] text-saral-yellow" />
        ) : (
          <BoltIcon className="text-[16px] text-saral-yellow" />
        )}
        <span>{isSimplifying ? 'Working…' : 'Simplify'}</span>
      </button>

      <button
        type="button"
        onClick={onTranslate}
        disabled={!canTranslate || isTranslating}
        aria-busy={isTranslating}
        className={`${baseButton} border-2 border-saral-ink bg-white text-saral-ink shadow-[3px_3px_0_0_#0D0D0D]`}
      >
        {isTranslating ? (
          <SpinnerIcon className="text-[16px]" />
        ) : (
          <TranslateIcon className="text-[16px]" />
        )}
        <span>{isTranslating ? 'Translating…' : 'Translate'}</span>
      </button>

      <button
        type="button"
        onClick={onReadAloud}
        disabled={!canReadAloud || isTtsLoading}
        aria-busy={isTtsLoading}
        className={`${baseButton} border-2 border-saral-ink bg-white text-saral-ink shadow-[3px_3px_0_0_#0D0D0D]`}
      >
        {isTtsLoading ? (
          <SpinnerIcon className="text-[16px]" />
        ) : (
          <VolumeIcon className="text-[16px]" />
        )}
        <span>{isTtsLoading ? 'Making audio…' : 'Read Aloud'}</span>
      </button>
    </section>
  );
}
