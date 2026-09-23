import { useEffect, useRef, useState } from 'react';
import { getAudioUrl, synthesizeSpeech } from '../services/api';

const comparisonData = [
  {
    title: 'Ration Card Form 7',
    complexity: 'Complexity: High (14.2)',
    length: 'Length: 48 words',
    legal: '“Pursuant to Sub-section (3) of Section 12-A of the Public Distribution Guidelines (2018 Revision), applicants failing to substantiate perpetual domicile certification within forty-five (45) calendar days from receipt of preliminary intimation shall suffer summary rejection without prejudice to fresh application submission.”',
    score: 'Readability: Grade 5.0',
    savings: 'Saved: 68% Reading Time',
    bullets: [
      'Submit your local address proof within 45 days of getting the letter.',
      'If you miss this date, your application will be cancelled.',
      'You can still apply again anytime.',
    ],
  },
  {
    title: 'EPFO Withdrawal Clause',
    complexity: 'Complexity: Extreme (16.8)',
    length: 'Length: 56 words',
    legal: '“In contemplation of Paragraph 68-B of the Employees’ Provident Funds Scheme, an entitlement for non-refundable premature liquidation may accrue solely upon continuous non-remunerative tenure exceeding sixty (60) days, requiring corroborative employer endorsement unless designated exceptions under clause 4 pertain.”',
    score: 'Readability: Grade 5.8',
    savings: 'Saved: 74% Reading Time',
    bullets: [
      'You can take out your PF money if you have been out of work for 2 months.',
      'You need your previous employer to sign the withdrawal form.',
      'Money is sent directly to your registered bank account.',
    ],
  },
  {
    title: 'Section 80D Deduction',
    complexity: 'Complexity: Very High (15.1)',
    length: 'Length: 44 words',
    legal: '“Where an assessee, being an individual or Hindu undivided family, pays during the previous year by any mode other than cash, an aggregate sum towards preventive medical diagnostic check-ups, the deduction allowable shall be capped strictly under statutory thresholds without cumulative rollover.”',
    score: 'Readability: Grade 4.9',
    savings: 'Saved: 62% Reading Time',
    bullets: [
      'You can claim tax deductions for health check-ups up to ₹5,000.',
      'Payments must be digital (UPI, card, or check) — cash is not allowed.',
      'Unused limit amounts cannot be carried forward to next year.',
    ],
  },
];

type ComparisonEngineProps = {
  activeTab: number;
  onSwitchTab: (index: number) => void;
};

export default function ComparisonEngine({ activeTab, onSwitchTab }: ComparisonEngineProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedLine, setHighlightedLine] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const intervalRef = useRef<number | null>(null);
  const lineRef = useRef(0);
  const current = comparisonData[activeTab];

  const clearPlayback = () => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setIsPlaying(false);
    setHighlightedLine(0);
    lineRef.current = 0;
  };

  useEffect(() => clearPlayback, [activeTab]);

  useEffect(() => () => clearPlayback(), []);

  const toggleAudio = async () => {
    if (isPlaying) {
      clearPlayback();
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await synthesizeSpeech(current.bullets.join(' '), 'en');
      const audio = new Audio(getAudioUrl(response.audio_url));
      audioRef.current = audio;
      audio.onended = () => clearPlayback();
      await audio.play();
      setIsPlaying(true);
      setHighlightedLine(1);
      lineRef.current = 1;
      intervalRef.current = window.setInterval(() => {
        if (!isPlaying) return;
        const next = lineRef.current + 1;
        if (next > current.bullets.length) {
          clearPlayback();
          return;
        }
        lineRef.current = next;
        setHighlightedLine(next);
      }, 1800);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audio service unavailable.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-10 reveal-section" id="comparison-section">
      <div className="bg-white stroke-border rounded-3xl p-6 sm:p-10 card-shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-8 border-b-2 border-neutral-100">
          <div>
            <div className="inline-block bg-[#F9C915] stroke-border-thin px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-2">INTERACTIVE COMPARISON ENGINE</div>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">See the transformation in action</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Comparison examples">
            {comparisonData.map((item, index) => (
              <button
                key={item.title}
                aria-selected={activeTab === index}
                className={`btn-tactile text-xs sm:text-sm font-bold px-4 py-2.5 rounded-full cursor-pointer transition-all ${activeTab === index ? 'bg-black text-white stroke-border' : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-800 stroke-border-thin'}`}
                onClick={() => onSwitchTab(index)}
                role="tab"
                type="button"
              >
                {item.title}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 mt-8">
          <div className="bg-neutral-50 stroke-border rounded-2xl p-6 flex flex-col justify-between card-shadow">
            <div>
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-neutral-200">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-red-600 rounded-sm animate-pulse"></span>
                  <span className="text-xs font-extrabold uppercase tracking-wider">OFFICIAL LEGAL TEXT</span>
                </div>
                <span className="bg-red-100 text-red-700 text-xs font-bold px-2.5 py-0.5 rounded-full stroke-border-thin">{current.complexity}</span>
              </div>
              <blockquote className="bg-white stroke-border-thin rounded-xl p-5 text-neutral-700 text-sm sm:text-base leading-relaxed italic transition-opacity duration-200">
                {current.legal}
              </blockquote>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold text-neutral-600 pt-4 mt-6 border-t border-neutral-200">
              <span>{current.length}</span>
              <span>Passive voice · Legal terminology</span>
            </div>
          </div>
          <div className="bg-[#F9C915] stroke-border rounded-2xl p-6 flex flex-col justify-between card-shadow">
            <div>
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-black/20">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-black rounded-full"></span>
                  <span className="text-xs font-extrabold uppercase tracking-wider">SARAL PLAIN ENGLISH</span>
                </div>
                <span className="bg-white text-black text-xs font-extrabold px-3 py-0.5 rounded-full stroke-border-thin">{current.score}</span>
              </div>
              <div className="bg-white stroke-border-thin rounded-xl p-6 space-y-3.5 transition-opacity duration-200">
                {current.bullets.map((bullet, index) => (
                  <div
                    key={`${activeTab}-${index}`}
                    className={`reading-line flex items-start gap-2.5 p-1 rounded transition-colors ${highlightedLine === index + 1 ? 'bg-white stroke-border-thin scale-[1.02] shadow-sm' : ''}`}
                  >
                    <span className="text-black font-black text-lg leading-none">•</span>
                    <p className="text-sm sm:text-base font-extrabold text-black">{bullet}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between pt-4 mt-6 border-t border-black/20">
              <button className="btn-tactile bg-black text-white hover:bg-neutral-800 text-xs font-bold px-4 py-2 rounded-full stroke-border flex items-center gap-2 cursor-pointer disabled:opacity-70 disabled:cursor-wait" disabled={isLoading} onClick={toggleAudio} type="button">
                <span>{isPlaying ? '⏸' : '▶'}</span>
                <span>{isPlaying ? 'Pause' : 'Play Aloud'}</span>
                <div className={`${isPlaying ? 'flex' : 'hidden'} items-center gap-0.5 h-3 eq-playing`} aria-hidden="true">
                  <span className="eq-bar !bg-white"></span>
                  <span className="eq-bar !bg-white"></span>
                  <span className="eq-bar !bg-white"></span>
                </div>
              </button>
              <span className="text-xs font-extrabold text-black bg-white/70 px-2.5 py-1 rounded-full stroke-border-thin">{current.savings}</span>
            </div>
          </div>
        </div>
        {error && (
          <div role="alert" className="mt-5 bg-[#FEF9C3] stroke-border-thin rounded-xl px-4 py-3 text-xs font-bold">
            Audio could not start. {error}
          </div>
        )}
      </div>
    </section>
  );
}
