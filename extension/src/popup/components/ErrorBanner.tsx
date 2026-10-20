import { CloseIcon, SpinnerIcon, WarningIcon } from './Icons';

type ErrorBannerProps = {
  title: string;
  message: string;
  tone?: 'error' | 'info';
  isBusy?: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
};

const TONE_STYLES = {
  error: 'bg-red-50 text-red-900 border-red-700',
  info: 'bg-saral-lavender text-saral-ink border-saral-ink',
} as const;

export default function ErrorBanner({
  title,
  message,
  tone = 'error',
  isBusy = false,
  onRetry,
  onDismiss,
}: ErrorBannerProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`brutal-card-sm flex items-start gap-2 border-2 p-2.5 ${TONE_STYLES[tone]}`}
    >
      {isBusy ? (
        <SpinnerIcon className="mt-0.5 shrink-0 text-[15px]" />
      ) : (
        <WarningIcon className="mt-0.5 shrink-0 text-[15px]" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-extrabold">{title}</p>
        <p className="mt-0.5 text-[11px] font-medium leading-snug">{message}</p>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            disabled={isBusy}
            className="btn-tactile brutal-pill-sm mt-1.5 bg-white px-2.5 py-0.5 text-[10px] font-extrabold text-saral-ink disabled:opacity-50"
          >
            {isBusy ? 'Retrying…' : 'Retry'}
          </button>
        ) : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss this message"
          className="focus-ring shrink-0 rounded-full p-0.5 hover:bg-black/10"
        >
          <CloseIcon className="text-[14px]" />
        </button>
      ) : null}
    </div>
  );
}
