import { useState } from 'react';
import type { FactItem } from '../../shared/facts';
import type { LanguageOption, UnavailableLanguageOption } from '../../shared/config';
import AudioDeck from './AudioDeck';
import FactList from './FactList';
import Markdown from './Markdown';
import { CheckIcon, CopyIcon, WarningIcon } from './Icons';

type SummaryCardProps = {
  simplifiedText: string;
  translatedText: string | null;
  translatedLanguageLabel: string | null;
  facts: FactItem[];
  hiddenFacts?: number;
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
  hiddenFacts = 0,
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
            className="h-2.5 w-2.5 rounded-full bg-saral-ink shadow-[1px_1px_0_0_#0D0D0D]"
            aria-hidden="true"
          />
          <h2 className="text-[12px] font-extrabold uppercase tracking-wider text-saral-ink">
            Instant Summary
          </h2>
        </div>
      </div>

      {/* ---- Important facts ---- */}
      <FactList facts={facts} hidden={hiddenFacts} />

      {/* ---- Simplified text ---- */}
      {/* The popup scrolls as one surface, so the text is not a second
          scroll area. The collapsed state is a preview; the button reveals
          the rest. */}
      <div className="rounded-lg border-2 border-saral-ink/15 bg-white p-2.5">
        <Markdown
          text={simplifiedText}
          className={`text-[12px] font-medium leading-relaxed text-saral-ink ${
            isExpanded ? '' : 'max-h-[170px] overflow-hidden'
          }`}
        />
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
          <Markdown
            text={translatedText}
            className="text-[12px] font-medium leading-relaxed text-saral-ink"
          />
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
                    : 'bg-white text-saral-ink hover:bg-neutral-100'
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
              className="brutal-pill-sm cursor-not-allowed bg-white px-2.5 py-1 text-[10px] font-bold text-saral-ink/40 line-through"
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
        <div
          role="status"
          className="rounded-lg bg-amber-50 p-2 text-[10px] font-bold text-amber-800"
        >
          <p className="flex items-start gap-1.5">
            <WarningIcon className="mt-0.5 shrink-0 text-[13px]" aria-hidden="true" />
            <span>Saral flagged issues in this simplification. Check it against the original.</span>
          </p>
          <ul className="mt-1 list-disc pl-4">
            {validationFailures.slice(0, 3).map((failure) => (
              <li key={failure} className="mt-0.5 leading-snug">
                {failure}
              </li>
            ))}
          </ul>
          {validationFailures.length > 3 ? (
            <p className="mt-1 pl-4">
              +{validationFailures.length - 3} more issue(s) found in the source comparison.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
