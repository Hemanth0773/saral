import { useEffect, useState } from 'react';
import { DEFAULT_BASE_URL, validateBaseUrl } from '../../shared/config';
import { CloseIcon, ExternalLinkIcon, GearIcon } from './Icons';

type SettingsPanelProps = {
  isOpen: boolean;
  baseUrl: string;
  onClose: () => void;
  onSave: (baseUrl: string) => Promise<void>;
  onOpenHelp: () => void;
};

export default function SettingsPanel({
  isOpen,
  baseUrl,
  onClose,
  onSave,
  onOpenHelp,
}: SettingsPanelProps) {
  const [draft, setDraft] = useState(baseUrl);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setDraft(baseUrl);
      setError(null);
    }
  }, [isOpen, baseUrl]);

  if (!isOpen) return null;

  async function handleSave() {
    const validation = validateBaseUrl(draft);
    if (!validation.ok || !validation.value) {
      setError(validation.message ?? 'That address is not valid.');
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await onSave(validation.value);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save the address.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="absolute inset-0 z-40 flex items-start justify-center bg-black/40 p-3"
      role="dialog"
      aria-modal="true"
      aria-label="Saral settings"
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
    >
      <div className="brutal-card w-full bg-white p-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-[12px] font-extrabold uppercase tracking-wider text-saral-ink">
            <GearIcon className="text-[15px]" aria-hidden="true" />
            Saral settings
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="focus-ring rounded-full p-1 hover:bg-black/10"
          >
            <CloseIcon className="text-[15px]" />
          </button>
        </div>

        <label
          htmlFor="saral-base-url"
          className="block text-[11px] font-extrabold text-saral-ink"
        >
          Backend address
        </label>
        <input
          id="saral-base-url"
          type="url"
          inputMode="url"
          spellCheck={false}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={DEFAULT_BASE_URL}
          className="mt-1 w-full rounded-lg border-2 border-saral-ink/40 bg-white px-2.5 py-2 text-[12px] font-medium text-saral-ink focus:outline-none focus:border-saral-ink"
        />
        <p className="mt-1 text-[10px] font-semibold text-saral-ink/55">
          Saral sends the text you approve to this address. Nothing is sent automatically.
        </p>

        {error ? (
          <p role="alert" className="mt-1.5 text-[10px] font-bold text-red-700">
            {error}
          </p>
        ) : null}

        <div className="mt-2.5 flex items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="btn-tactile brutal-pill-sm bg-saral-ink px-3 py-1 text-[11px] font-extrabold text-white disabled:opacity-50"
          >
            {isSaving ? 'Saving…' : 'Save address'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="brutal-pill-sm bg-white px-3 py-1 text-[11px] font-extrabold text-saral-ink"
          >
            Cancel
          </button>
        </div>

        <button
          type="button"
          onClick={onOpenHelp}
          className="focus-ring mt-2.5 inline-flex items-center gap-1 text-[10px] font-extrabold text-saral-ink underline decoration-saral-yellow decoration-2 underline-offset-2"
        >
          <span>Help &amp; Docs</span>
          <ExternalLinkIcon className="text-[12px]" />
        </button>
      </div>
    </div>
  );
}
