import { useState, useRef, useEffect } from 'react';
import { getAudioUrl, synthesizeSpeech, type TTSResponse } from '../services/api';

type AudioPlaybackSectionProps = {
  initialText?: string;
};

const supportedLanguages = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'Kannada' }
];

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function AudioPlaybackSection({ initialText }: AudioPlaybackSectionProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'kn'>('en');
  const [sourceText, setSourceText] = useState(initialText || '');
  const [userHasEdited, setUserHasEdited] = useState(false);
  const [ttsResult, setTtsResult] = useState<TTSResponse | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolume] = useState(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Handle external prefill (only if user hasn't edited)
  useEffect(() => {
    if (initialText && !userHasEdited) {
      setSourceText(initialText);
    }
  }, [initialText, userHasEdited]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSourceText(e.target.value);
    if (!userHasEdited && e.target.value.trim().length > 0) {
      setUserHasEdited(true);
    }
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      if (audio.duration) {
        setDuration(audio.duration);
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    };

    const handleTimeUpdate = () => updateProgress();
    const handleEnded = () => {
      setPlaying(false);
      setProgress(0);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('loadedmetadata', updateProgress);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('loadedmetadata', updateProgress);
    };
  }, []);

  const handleGenerateAudio = async () => {
    const text = sourceText.trim();
    if (!text) {
      setError('Enter text to convert to speech.');
      return;
    }

    setLoading(true);
    setError(null);
    setTtsResult(null);

    try {
      const response = await synthesizeSpeech(text, selectedLanguage);
      setTtsResult(response);

      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audioUrl = getAudioUrl(response.audio_url);
      const audio = new Audio(audioUrl);
      audio.volume = volume;
      audioRef.current = audio;

      await audio.play();
      setPlaying(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audio generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().catch(() => setError('Playback failed.'));
      setPlaying(true);
    }
  };

  const handleStop = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      setPlaying(false);
      setProgress(0);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const clickPosition = (e.clientX - rect.left) / rect.width;
    audio.currentTime = clickPosition * audio.duration;
    setProgress(clickPosition * 100);
  };

  return (
    <section className="max-w-7xl mx-auto px-6 lg:px-12 py-12 reveal-section" id="audio-section">
      <div className="bg-white stroke-border rounded-3xl p-8 sm:p-12 card-shadow-lg">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-block bg-[#F9C915] stroke-border-thin px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider mb-3">3 / AUDIO PLAYBACK</div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">Listen to Saral</h2>
          <p className="text-neutral-700 font-medium text-base">Hear simplified government information in a clear, natural voice.</p>
        </div>
        <div className="max-w-3xl mx-auto">
          <div className="bg-neutral-50 stroke-border rounded-2xl p-6 mb-6">
            <label className="block text-xs font-extrabold uppercase tracking-wider mb-3 text-neutral-800">Text to listen</label>
            <textarea
              className="w-full bg-white stroke-border-thin rounded-xl px-4 py-3 text-sm font-medium placeholder:text-neutral-400 resize-none min-h-[100px] focus:ring-2 focus:ring-black focus:border-black outline-none"
              onChange={handleInputChange}
              placeholder="Enter or paste text to hear it..."
              value={sourceText}
            />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 mb-6">
            <span className="text-xs font-extrabold uppercase tracking-wider text-neutral-800">CHOOSE LANGUAGE:</span>
            {supportedLanguages.map((lang) => (
              <button
                key={lang.code}
                className={`btn-tactile text-xs font-bold px-3 py-1.5 rounded-full stroke-border flex items-center gap-1.5 cursor-pointer transition-all ${selectedLanguage === lang.code ? 'bg-black text-white' : 'bg-white hover:bg-neutral-100 text-black'}`}
                onClick={() => setSelectedLanguage(lang.code as 'en' | 'kn')}
                type="button"
              >
                <span>{lang.label === 'Kannada' ? '🇮🇳' : '🇬🇧'}</span>
                <span>{lang.label}</span>
              </button>
            ))}
          </div>
          <div className="space-y-4">
            <div className="bg-white stroke-border rounded-2xl p-5 flex items-center gap-4">
              <button
                className={`btn-tactile w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${playing ? 'bg-black text-white' : 'bg-neutral-100 text-black hover:bg-neutral-200'}`}
                onClick={handlePlayPause}
                disabled={loading || !ttsResult}
                type="button"
                aria-label={playing ? 'Pause' : 'Play'}
              >
                {playing ? (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                ) : (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                )}
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex items-center gap-1.5 eq-playing" aria-hidden="true" style={{ opacity: playing ? 1 : 0.3 }}>
                    <span className="w-[2px] h-2 bg-black rounded-full"></span>
                    <span className="w-[2px] h-3 bg-black rounded-full"></span>
                    <span className="w-[2px] h-[6px] bg-black rounded-full"></span>
                    <span className="w-[2px] h-4 bg-black rounded-full"></span>
                    <span className="w-[2px] h-[6px] bg-black rounded-full"></span>
                  </div>
                  <span className="text-xs font-bold text-neutral-500 uppercase tracking-wider">Voice: {selectedLanguage === 'kn' ? 'Kannada Neural' : 'English US'}</span>
                </div>
                <div className="w-full h-2 bg-neutral-200 stroke-border-thin rounded-full overflow-hidden" onClick={handleProgressClick}>
                  <div
                    className="h-full bg-black transition-all duration-100"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] font-bold text-neutral-500 mt-1">
                  <span>{formatTime(audioRef.current?.currentTime || 0)}</span>
                  <span>{duration > 0 ? formatTime(duration) : '0:00'}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  className="btn-tactile w-10 h-10 rounded-full stroke-border bg-white flex items-center justify-center hover:bg-neutral-100 transition-colors"
                  onClick={handleStop}
                  disabled={!playing && progress === 0}
                  type="button"
                  aria-label="Stop"
                >
                  <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                </button>
                <div className="flex items-center gap-1">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={volume === 0}
                      onChange={() => setVolume(volume === 0 ? 1 : 0)}
                      className="w-4 h-4 accent-black"
                    />
                    <svg className={`w-5 h-5 text-black ${volume === 0 ? 'opacity-30' : ''}`} fill="currentColor" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={volume}
                    onChange={handleVolumeChange}
                    className="w-20 h-2 accent-black appearance-none rounded-lg bg-neutral-200"
                    aria-label="Volume"
                  />
                </div>
              </div>
            </div>
            <button className="btn-tactile w-full bg-black hover:bg-neutral-900 text-white font-extrabold text-sm py-4 rounded-xl stroke-border flex items-center justify-center gap-2 group cursor-pointer disabled:opacity-70 disabled:cursor-wait" disabled={loading} onClick={handleGenerateAudio} type="button">
              <span>{loading ? 'Generating Audio...' : (ttsResult ? 'Regenerate Audio →' : 'Play Audio →')}</span>
              <span className={`group-hover:translate-x-1.5 transition-transform duration-200 ${loading ? 'hidden' : ''}`}>→</span>
              <svg className={`animate-spin h-5 w-5 text-white ${loading ? 'block' : 'hidden'}`} fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
              </svg>
            </button>
          </div>
          {error && (
            <div role="alert" className="mt-6 bg-[#FEF9C3] stroke-border-thin rounded-xl px-4 py-3 text-xs font-bold text-black text-center">
              {error}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}