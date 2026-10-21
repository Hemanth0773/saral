import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { saralApi } from '../services/api';
import { createInFlightGuard } from './guards';
import ActionBar from './components/ActionBar';
import EmptyStateCard from './components/EmptyStateCard';
import ErrorBanner from './components/ErrorBanner';
import Footer from './components/Footer';
import Header from './components/Header';
import HeroCard from './components/HeroCard';
import InputCard from './components/InputCard';
import SettingsPanel from './components/SettingsPanel';
import SummaryCard from './components/SummaryCard';
import {
  ALLOWED_FILE_EXTENSIONS,
  DEFAULT_BASE_URL,
  MAX_FILE_SIZE_BYTES,
  MAX_SIMPLIFY_TEXT_LENGTH,
  SUPPORTED_LANGUAGES,
  TARGET_GRADE_LEVEL,
  UNAVAILABLE_LANGUAGES,
  getFileExtension,
  joinUrl,
} from '../shared/config';
import { describeError, toSaralError } from '../shared/errors';
import { buildFactSummary, toFactItem } from '../shared/facts';
import type {
  ExtractionResponse,
  SimplificationResponse,
  TranslationResponse,
  TTSResponse,
} from '../types/api';

type Banner = {
  title: string;
  message: string;
  retryable: boolean;
  tone: 'error' | 'info';
};

type CopyState = 'idle' | 'copied' | 'failed';

const URL_PATTERN = /^https?:\/\/\S+$/i;

function looksLikeUrl(value: string): boolean {
  return URL_PATTERN.test(value.trim());
}

export default function App() {
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isReading, setIsReading] = useState(false);
  const [sourceNote, setSourceNote] = useState<string | null>(null);
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null);

  const [isSimplifying, setIsSimplifying] = useState(false);
  const [simplification, setSimplification] = useState<SimplificationResponse | null>(null);
  const [structured, setStructured] = useState<ExtractionResponse | null>(null);

  const [activeLanguage, setActiveLanguage] = useState('en');
  const [translation, setTranslation] = useState<TranslationResponse | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);

  const [tts, setTts] = useState<TTSResponse | null>(null);
  const [isTtsLoading, setIsTtsLoading] = useState(false);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const [speed, setSpeed] = useState(1);

  const [copyState, setCopyState] = useState<CopyState>('idle');
  const [banner, setBanner] = useState<Banner | null>(null);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const lastAction = useRef<(() => void) | null>(null);
  // Ensures a single Simplify request can be in flight at a time.
  const simplifyGuard = useRef(createInFlightGuard()).current;

  useEffect(() => {
    let cancelled = false;
    saralApi
      .getConfig()
      .then((config) => {
        if (!cancelled) setBaseUrl(config.baseUrl);
      })
      .catch(() => {
        /* Keep the default; the user can still change it in settings. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const showError = useCallback((error: unknown, retry?: () => void) => {
    const friendly = describeError(toSaralError(error));
    lastAction.current = retry ?? null;
    setBanner({
      title: friendly.title,
      message: friendly.message,
      retryable: friendly.retryable && Boolean(retry),
      tone: 'error',
    });
  }, []);

  const resetResult = useCallback(() => {
    setSimplification(null);
    setStructured(null);
    setTranslation(null);
    setTts(null);
    setTtsError(null);
    setCopyState('idle');
  }, []);

  /* ------------------------------------------------------------------ */
  /* Read active tab / selection                                        */
  /* ------------------------------------------------------------------ */
  const handleReadActiveTab = useCallback(async () => {
    setIsReading(true);
    setBanner(null);
    try {
      const content = await saralApi.extractActiveTab();
      if (!content.text.trim()) {
        setBanner({
          title: 'No readable text found',
          message:
            'Saral could not find article text on this page. Select the text you want and paste it into the box, or try a different page.',
          retryable: true,
          tone: 'error',
        });
        lastAction.current = () => {
          void handleReadActiveTab();
        };
        return;
      }
      setText(content.text);
      setFile(null);
      setFileError(null);
      setDetectedLanguage(null);
      const where = content.source === 'selection' ? 'your selection' : 'the main page content';
      setSourceNote(
        `Read ${where} from ${content.title || content.url || 'this page'} · ${content.charCount.toLocaleString()} characters. Nothing has been sent yet.`,
      );
    } catch (error) {
      showError(error, () => {
        void handleReadActiveTab();
      });
    } finally {
      setIsReading(false);
    }
  }, [showError]);

  /* ------------------------------------------------------------------ */
  /* File upload                                                        */
  /* ------------------------------------------------------------------ */
  const handleSelectFile = useCallback(
    async (selected: File) => {
      const extension = getFileExtension(selected.name);
      if (!ALLOWED_FILE_EXTENSIONS.includes(extension as (typeof ALLOWED_FILE_EXTENSIONS)[number])) {
        setFileError(
          `Saral cannot read .${extension || 'unknown'} files. Allowed: ${ALLOWED_FILE_EXTENSIONS.join(', ')}.`,
        );
        setFile(null);
        return;
      }
      if (selected.size > MAX_FILE_SIZE_BYTES) {
        setFileError(
          `That file is ${(selected.size / (1024 * 1024)).toFixed(1)}MB. The backend accepts up to 10MB.`,
        );
        setFile(null);
        return;
      }
      if (selected.size === 0) {
        setFileError('That file is empty.');
        setFile(null);
        return;
      }

      setFileError(null);
      setFile(selected);
      setIsReading(true);
      setBanner(null);
      try {
        const result = await saralApi.extractFile(selected);
        setText(result.text);
        setDetectedLanguage(result.language);
        setSourceNote(
          `Extracted ${result.metadata.word_count.toLocaleString()} words from ${result.filename}. Nothing has been sent yet.`,
        );
        resetResult();
      } catch (error) {
        showError(error, () => {
          void handleSelectFile(selected);
        });
      } finally {
        setIsReading(false);
      }
    },
    [resetResult, showError],
  );

  /* ------------------------------------------------------------------ */
  /* Simplify                                                           */
  /* ------------------------------------------------------------------ */
  const handleSimplify = useCallback(async () => {
    // A second click while a request is running must not start another one.
    if (!simplifyGuard.tryStart()) return;

    const trimmed = text.trim();
    if (!trimmed && !file) {
      simplifyGuard.finish();
      setBanner({
        title: 'Nothing to simplify',
        message: 'Read the active tab, attach a document, or paste the notice text first.',
        retryable: false,
        tone: 'error',
      });
      return;
    }
    if (trimmed.length > MAX_SIMPLIFY_TEXT_LENGTH) {
      simplifyGuard.finish();
      setBanner({
        title: 'Text too long',
        message: `Saral sends at most ${MAX_SIMPLIFY_TEXT_LENGTH.toLocaleString()} characters at a time. Please shorten the text.`,
        retryable: false,
        tone: 'error',
      });
      return;
    }

    setIsSimplifying(true);
    setBanner(null);
    setIsTranslating(false);
    setTranslation(null);
    setTts(null);
    setTtsError(null);

    try {
      let sourceText = trimmed;
      let detected: string | null = detectedLanguage;

      // A pasted portal URL is fetched by the backend so its SSRF protection
      // and extraction pipeline stay in one place.
      if (!file && looksLikeUrl(trimmed)) {
        setIsReading(true);
        const extracted = await saralApi.extractUrl(trimmed);
        setIsReading(false);
        sourceText = extracted.text;
        detected = extracted.language;
        setText(extracted.text);
        setSourceNote(
          `Fetched ${extracted.metadata.word_count.toLocaleString()} words from ${extracted.source_url}.`,
        );
      }

      const result = await saralApi.simplify(sourceText, TARGET_GRADE_LEVEL);
      setSimplification(result);
      setDetectedLanguage(detected);

      // The backend measures the readability together with the simplification,
      // so nothing here can fail and lose the result the user already got.

      // The backend builds the canonical Instant Summary. Only an older
      // backend that does not return it needs the structured extraction.
      if (!result.instant_summary || !result.instant_summary.length) {
        void saralApi.extractInfo(sourceText).then(setStructured);
      }
    } catch (error) {
      showError(error, () => {
        void handleSimplify();
      });
    } finally {
      setIsReading(false);
      setIsSimplifying(false);
      simplifyGuard.finish();
    }
  }, [detectedLanguage, file, showError, simplifyGuard, text]);

  /* ------------------------------------------------------------------ */
  /* Translate                                                          */
  /* ------------------------------------------------------------------ */
  const runTranslation = useCallback(
    async (targetLanguage: string) => {
      if (!simplification) return;
      if (targetLanguage === 'en') {
        setTranslation(null);
        return;
      }
      setIsTranslating(true);
      setBanner(null);
      try {
        const result = await saralApi.translate(
          simplification.simplified_text,
          'en',
          targetLanguage,
        );
        setTranslation(result);
      } catch (error) {
        showError(error, () => {
          void runTranslation(targetLanguage);
        });
      } finally {
        setIsTranslating(false);
      }
    },
    [showError, simplification],
  );

  const handleSelectLanguage = useCallback(
    (code: string) => {
      setActiveLanguage(code);
      void runTranslation(code);
    },
    [runTranslation],
  );

  /* ------------------------------------------------------------------ */
  /* Text to speech                                                     */
  /* ------------------------------------------------------------------ */
  const handleReadAloud = useCallback(async () => {
    if (!simplification) return;
    const useKannada = activeLanguage === 'kn' && translation?.translated_text;
    const spokenText = useKannada
      ? (translation?.translated_text as string)
      : simplification.simplified_text;
    const language = useKannada ? 'kn' : 'en';

    setIsTtsLoading(true);
    setTtsError(null);
    setBanner(null);
    try {
      const result = await saralApi.synthesizeSpeech(spokenText, language, speed);
      setTts(result);
    } catch (error) {
      const friendly = describeError(toSaralError(error));
      setTtsError(friendly.message);
    } finally {
      setIsTtsLoading(false);
    }
  }, [activeLanguage, simplification, speed, translation]);

  /* ------------------------------------------------------------------ */
  /* Copy                                                               */
  /* ------------------------------------------------------------------ */
  const handleCopy = useCallback(async () => {
    const source =
      activeLanguage === 'kn' && translation?.translated_text
        ? translation.translated_text
        : simplification?.simplified_text ?? '';
    if (!source) {
      setCopyState('failed');
      return;
    }
    try {
      await navigator.clipboard.writeText(source);
      setCopyState('copied');
    } catch {
      setCopyState('failed');
    }
    window.setTimeout(() => setCopyState('idle'), 1800);
  }, [activeLanguage, simplification, translation]);

  /* ------------------------------------------------------------------ */
  /* Settings + help                                                    */
  /* ------------------------------------------------------------------ */
  const handleSaveBaseUrl = useCallback(
    async (nextBaseUrl: string) => {
      const config = await saralApi.setConfig(nextBaseUrl);
      setBaseUrl(config.baseUrl);
      setIsSettingsOpen(false);
    },
    [],
  );

  const handleOpenHelp = useCallback(() => {
    void chrome.tabs.create({ url: chrome.runtime.getURL('help.html') });
  }, []);

  const factSummary = useMemo(() => {
    // The canonical summary comes from the backend, so the website and the
    // extension always show the same facts. The client side derivation is
    // only a fallback for an older backend that does not return it.
    const canonical = simplification?.instant_summary;
    if (canonical && canonical.length) {
      const facts = canonical.map(toFactItem);
      return { facts, total: facts.length, hidden: 0 };
    }
    return buildFactSummary(structured?.structured_information, simplification?.preserved_facts);
  }, [simplification, structured]);

  const audioUrl = useMemo(() => (tts ? joinUrl(baseUrl, tts.audio_url) : null), [baseUrl, tts]);

  const hiddenFacts = useMemo(() => {
    const hidden = simplification?.metadata?.summary_hidden;
    return typeof hidden === 'number' ? hidden : 0;
  }, [simplification]);

  const canSimplify = Boolean(text.trim() || file) && !isSimplifying && !isReading;
  const canTranslate = Boolean(simplification) && !isTranslating;
  const canReadAloud = Boolean(simplification) && !isTtsLoading;

  return (
      <div className="relative flex h-full max-h-[600px] w-[400px] flex-col overflow-hidden rounded-xl bg-saral-yellow">
      <Header onOpenSettings={() => setIsSettingsOpen(true)} />

      <main className="scroll-area flex-1 overflow-y-auto px-3 pb-3 pt-3">
        <div className="flex flex-col gap-2.5">
          <HeroCard />

          <InputCard
            value={text}
            onChange={(value) => {
              setText(value);
              setSourceNote(null);
              setFileError(null);
            }}
            onReadActiveTab={handleReadActiveTab}
            onSelectFile={handleSelectFile}
            onClear={() => {
              setText('');
              setFile(null);
              setFileError(null);
              setSourceNote(null);
              setDetectedLanguage(null);
              resetResult();
            }}
            file={file}
            fileError={fileError}
            isReading={isReading}
            detectedLanguage={detectedLanguage}
            sourceNote={sourceNote}
          />

          <ActionBar
            onSimplify={handleSimplify}
            onTranslate={() => {
              void runTranslation(activeLanguage === 'en' ? 'kn' : activeLanguage);
            }}
            onReadAloud={handleReadAloud}
            isSimplifying={isSimplifying}
            isTranslating={isTranslating}
            isTtsLoading={isTtsLoading}
            canSimplify={canSimplify}
            canTranslate={canTranslate}
            canReadAloud={canReadAloud}
          />

          {banner ? (
            <ErrorBanner
              title={banner.title}
              message={banner.message}
              tone={banner.tone}
              onRetry={banner.retryable && lastAction.current ? () => lastAction.current?.() : undefined}
              onDismiss={() => setBanner(null)}
            />
          ) : null}

          {simplification ? (
            <SummaryCard
              simplifiedText={simplification.simplified_text}
              translatedText={translation?.translated_text ?? null}
              translatedLanguageLabel={
                translation ? `Translation · ${translation.target_language.toUpperCase()}` : null
              }
              facts={factSummary.facts}
              hiddenFacts={hiddenFacts}
              validationPassed={simplification.validation_passed}
              validationFailures={simplification.validation_failures}
              modelUsed={simplification.model_used}
              processingTimeMs={simplification.processing_time_ms}
              audioUrl={audioUrl}
              isTtsLoading={isTtsLoading}
              ttsError={ttsError}
              speed={speed}
              onSpeedChange={setSpeed}
              languages={SUPPORTED_LANGUAGES}
              unavailableLanguages={UNAVAILABLE_LANGUAGES}
              activeLanguage={activeLanguage}
              onSelectLanguage={handleSelectLanguage}
              onCopy={handleCopy}
              copyState={copyState}
            />
          ) : (
            <EmptyStateCard isReading={isReading} />
          )}
        </div>
      </main>

      <Footer onOpenHelp={handleOpenHelp} />

      <SettingsPanel
        isOpen={isSettingsOpen}
        baseUrl={baseUrl}
        onClose={() => setIsSettingsOpen(false)}
        onSave={handleSaveBaseUrl}
        onOpenHelp={handleOpenHelp}
      />
    </div>
  );
}
