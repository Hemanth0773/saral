import { useState } from 'react';
import type { FactItem } from '../../shared/facts';
import type { LanguageOption, UnavailableLanguageOption } from '../../shared/config';
import AudioDeck from './AudioDeck';
import FactList from './FactList';
import { CheckCircleIcon, CheckIcon, CopyIcon, WarningIcon } from './Icons';

type SummaryCardProps = {
  simplifiedText: string;
  translatedText: string | null;
  translatedLanguageLabel: string | null;
  facts: FactItem[];
  gradeLabel: string | null;
  validationPassed: boolean;
  validationFailures: string[];
  modelUsed: string;
  processingTimeMs: number;
  audioUrl: string | null;
  isTtsLoading: boolean;
  ttsError: string | null;
  speed: number;
  onSpeedChange: (speed: number) => void;
  languages: LanguageOption[];
  unavailableLanguages: UnavailableLanguageOption[];
  activeLanguage: string;
  onSelectLanguage: (code: string) => void;
  onCopy: () => void;
  copyState: 'idle' | 'copied' | 'failed';
};

export default function SummaryCard({
  simplifiedText,
  translatedText,
  translatedLanguageLabel,
  facts,
  gradeLabel,
  validationPassed,
  validationFailures,
  modelUsed,
  processingTimeMs,
  audioUrl,
  isTtsLoading,
  ttsError,
  speed,
  onSpeedChange,
  languages,
  unavailableLanguages,
  activeLanguage,
  onSelectLanguage,
  onCopy,
  copyState,
}: SummaryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <section className="brutal-card flex flex-col gap-2.5 bg-white p-3">
      {/* ---- Status header ---- */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-full bg-saral-yellow shadow-[1px_1px_0_0_#0D0D0D]"
            aria-hidden="true"
          />
          <h2 className="text-[12px] font-extrabold uppercase tracking-wider text-saral-ink">
            Instant Summary
          </h2>
        </div>

        {gradeLabel ? (
          <span className="brutal-pill-sm inline-flex items-center gap-1 bg-saral-lavenderHigh px-2 py-0.5">
            <CheckCircleIcon className="text-[13px] text-saral-ink" aria-hidden="true" />
            <span className="text-[10px] font-extrabold text-saral-ink">{gradeLabel}</span>
          </span>
        ) : (
          <span className="brutal-pill-sm inline-flex items-center gap-1 bg-saral-lavender px-2 py-0.5">
            <span className="text-[10px] font-bold text-saral-ink/70">Grade not measured</span>
          </span>
        )}
      </div>

      {/* ---- Important facts ---- */}
      <FactList facts={facts} />

      {/* ---- Simplified text ---- */}
      <div className="rounded-lg border-2 border-saral-ink/15 bg-saral-lavender p-2.5">
        <p
          className={`scroll-area whitespace-pre-wrap text-[12px] font-medium leading-relaxed text-saral-ink ${
            isExpanded ? '' : 'max-h-[150px] overflow-y-auto'
          }`}
        >
          {simplifiedText}
        </p>
        {simplifiedText.length > 420 ? (
          <button
            type="button"
            onClick={() => setIsExpanded((expanded) => !expanded)}
            className="focus-ring mt-1.5 text-[10px] font-extrabold text-saral-ink underline"
          >
            {isExpanded ? 'Show less' : 'Show full text'}
          </button>
        ) : null}
      </div>

      {/* ---- Translated text ---- */}
      {translatedText ? (
        <div className="rounded-lg border-2 border-saral-ink/25 bg-white p-2.5">
          <p className="mb-1 text-[9px] font-extrabold uppercase tracking-wider text-saral-ink/50">
            {translatedLanguageLabel ?? 'Translation'}
          </p>
          <p className="scroll-area max-h-[130px] overflow-y-auto whitespace-pre-wrap text-[12px] font-medium leading-relaxed text-saral-ink">
            {translatedText}
          </p>
        </div>
      ) : null}

      {/* ---- Audio ---- */}
      <AudioDeck
        audioUrl={audioUrl}
        isLoading={isTtsLoading}
        error={ttsError}
        speed={speed}
        onSpeedChange={onSpeedChange}
      />

      {/* ---- Languages + copy ---- */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <div className="flex min-w-0 flex-wrap items-center gap-1">
          {languages.map((language) => {
            const isActive = language.code === activeLanguage;
            return (
              <button
                key={language.code}
                type="button"
                onClick={() => onSelectLanguage(language.code)}
                aria-pressed={isActive}
                className={`brutal-pill-sm px-2.5 py-1 text-[10px] font-bold ${
                  isActive
                    ? 'bg-saral-yellow text-saral-ink font-extrabold'
                    : 'bg-saral-lavenderHigh text-saral-ink hover:bg-saral-lavenderHighest'
                }`}
              >
                {language.native}
              </button>
            );
          })}

          {unavailableLanguages.map((language) => (
            <button
              key={language.code}
              type="button"
              disabled
              aria-disabled="true"
              title={language.reason}
              className="brutal-pill-sm cursor-not-allowed bg-saral-lavender px-2.5 py-1 text-[10px] font-bold text-saral-ink/40 line-through"
            >
              {language.native}
              <span className="ml-1 no-underline">Unavailable</span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onCopy}
          className="btn-tactile brutal-pill-sm inline-flex shrink-0 items-center gap-1 bg-white px-2.5 py-1 text-[10px] font-bold text-saral-ink"
        >
          {copyState === 'copied' ? (
            <CheckIcon className="text-[14px]" />
          ) : (
            <CopyIcon className="text-[14px]" />
          )}
          <span>{copyState === 'copied' ? 'Copied!' : copyState === 'failed' ? 'Failed' : 'Copy'}</span>
        </button>
      </div>

      {/* ---- Provenance ---- */}
      <p className="text-[9px] font-semibold text-saral-ink/45">
        {modelUsed ? `Model: ${modelUsed} · ` : ''}
        {processingTimeMs ? `${(processingTimeMs / 1000).toFixed(1)}s` : ''}
        {!validationPassed ? ' · fact check flagged issues' : ''}
      </p>

      {!validationPassed && validationFailures.length ? (
        <p
          role="status"
          className="flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 text-[10px] font-bold text-amber-800"
        >
          <WarningIcon className="mt-0.5 shrink-0 text-[13px]" aria-hidden="true" />
          <span>
            Saral could not confirm that every fact was preserved
            {validationFailures.length ? `: ${validationFailures.slice(0, 2).join('; ')}` : '.'}
          </span>
        </p>
      ) : null}
    </section>
  );
}
