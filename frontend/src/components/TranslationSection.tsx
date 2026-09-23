import { useState, useEffect, useRef } from 'react';
import { translateText, type TranslationResponse } from '../services/api';

type TranslationSectionProps = {
  initialText?: string;
  onTranslationComplete?: (text: string, language: 'en' | 'kn') => void;
};

const supportedLanguages = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'Kannada' }
];

export default function TranslationSection({ initialText, onTranslationComplete }: TranslationSectionProps) {
  const [inputText, setInputText] = useState(initialText || '');
  const [userHasEdited, setUserHasEdited] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState<'en' | 'kn'>('kn');
  const [translating, setTranslating] = useState(false);
  const [translationResult, setTranslationResult] = useState<TranslationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  // Track if user has manually edited the input
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (!userHasEdited && e.target.value.trim().length > 0) {
      setUserHasEdited(true);
    }
  };

  // Handle external prefill (only if user hasn't edited)
  useEffect(() => {
    if (initialText && !userHasEdited) {
      setInputText(initialText);
    }
  }, [initialText, userHasEdited]);

  const handleTranslate = async () => {
    const text = inputText.trim();
    if (!text) {
      setError('Enter text to translate.');
      return;
    }

    // Detect source language: if text contains Kannada characters, source is 'kn'
    const hasKannada = /[\u0C80-\u0CFF]/.test(inputText);
    const sourceLanguage = hasKannada ? 'kn' : 'en';

    setTranslating(true);
    setError(null);
    setTranslationResult(null);

    try {
      const response = await translateText(inputText, sourceLanguage, targetLanguage);
      setTranslationResult(response);
      if (onTranslationComplete) {
        onTranslationComplete(response.translated_text, targetLanguage);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Translation failed.');
    } finally {
      setTranslating(false);
    }
  };

  useEffect(() => {
    textAreaRef.current?.focus();
  }, []);

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section" id="translation-section">
      <div className="bg-white stroke-border rounded-3xl p-8 sm:p-12 card-shadow-lg">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-block bg-[#F9C915] stroke-border-thin px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-3">2 / TRANSLATION</div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">Translate into your language</h2>
          <p className="text-neutral-700 font-medium text-base">Make simplified government information easier to understand in your preferred language.</p>
        </div>
        <div className="max-w-3xl mx-auto">
          <div className="bg-neutral-50 stroke-border rounded-2xl p-6 mb-6">
            <label className="block text-xs font-extrabold uppercase tracking-wider mb-3 text-neutral-800">Text to translate</label>
            <textarea
              ref={textAreaRef}
              className="w-full bg-white stroke-border-thin rounded-xl px-4 py-3 text-sm font-medium placeholder:text-neutral-400 resize-none min-h-[120px] focus:ring-2 focus:ring-black focus:border-black outline-none"
              onChange={handleInputChange}
              placeholder="Enter or paste text to translate..."
              value={inputText}
            />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 mb-6">
            <span className="text-xs font-extrabold uppercase tracking-wider text-neutral-800">CHOOSE LANGUAGE:</span>
            {supportedLanguages.map((lang) => (
              <button
                key={lang.code}
                className={`btn-tactile text-xs font-bold px-3 py-1.5 rounded-full stroke-border flex items-center gap-1.5 cursor-pointer transition-all ${targetLanguage === lang.code ? 'bg-black text-white' : 'bg-white hover:bg-neutral-100 text-black'}`}
                onClick={() => setTargetLanguage(lang.code as 'en' | 'kn')}
                type="button"
              >
                <span>{lang.label === 'Kannada' ? '🇮🇳' : '🇬🇧'}</span>
                <span>{lang.label}</span>
              </button>
            ))}
          </div>
          <button className="btn-tactile w-full bg-black hover:bg-neutral-900 text-white font-extrabold text-sm py-4 rounded-xl stroke-border flex items-center justify-center gap-2 group cursor-pointer disabled:opacity-70 disabled:cursor-wait" disabled={translating} onClick={handleTranslate} type="button">
            <span>{translating ? 'Translating...' : 'Translate →'}</span>
            <span className={`group-hover:translate-x-1.5 transition-transform duration-200 ${translating ? 'hidden' : ''}`}>→</span>
            <svg className={`animate-spin h-5 w-5 text-white ${translating ? 'block' : 'hidden'}`} fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
            </svg>
          </button>
          {error && (
            <div role="alert" className="mt-6 bg-[#FEF9C3] stroke-border-thin rounded-xl px-4 py-3 text-xs font-bold text-black text-center">
              {error}
            </div>
          )}
          {translationResult && (
            <div className="mt-6 bg-[#FEF9C3] stroke-border rounded-2xl p-5 text-left">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-black/15">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-black rounded-full"></span>
                  <span className="text-xs font-extrabold uppercase tracking-wider">Translated text ({targetLanguage === 'kn' ? 'Kannada' : 'English'})</span>
                </div>
                <span className="text-xs font-extrabold text-neutral-500">Ready</span>
              </div>
              <div className="bg-white stroke-border-thin rounded-xl p-4 min-h-[100px] whitespace-pre-wrap break-words text-sm leading-relaxed text-neutral-700">
                {translationResult.translated_text}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}