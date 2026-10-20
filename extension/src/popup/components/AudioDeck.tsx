import { useEffect, useRef, useState } from 'react';
import { PauseIcon, PlayIcon, SpinnerIcon, VolumeIcon } from './Icons';

type AudioDeckProps = {
  audioUrl: string | null;
  isLoading: boolean;
  error: string | null;
  speed: number;
  onSpeedChange: (speed: number) => void;
};

const SPEEDS = [1, 1.25, 1.5, 0.75];

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${rest.toString().padStart(2, '0')}`;
}

export default function AudioDeck({
  audioUrl,
  isLoading,
  error,
  speed,
  onSpeedChange,
}: AudioDeckProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackFailed, setPlaybackFailed] = useState(false);

  useEffect(() => {
    setPlaybackFailed(false);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);

    if (!audioUrl) {
      audioRef.current = null;
      return;
    }

    const audio = new Audio(audioUrl);
    audio.preload = 'metadata';
    audio.volume = volume;
    audio.playbackRate = speed;
    audioRef.current = audio;

    const handleLoaded = () => {
      setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
    };
    const handleTime = () => setCurrentTime(audio.currentTime);
    const handleEnded = () => setIsPlaying(false);
    const handleError = () => {
      setPlaybackFailed(true);
      setIsPlaying(false);
    };

    audio.addEventListener('loadedmetadata', handleLoaded);
    audio.addEventListener('durationchange', handleLoaded);
    audio.addEventListener('timeupdate', handleTime);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.pause();
      audio.removeEventListener('loadedmetadata', handleLoaded);
      audio.removeEventListener('durationchange', handleLoaded);
      audio.removeEventListener('timeupdate', handleTime);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
    // `volume` and `speed` are applied through the dedicated handlers below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed;
  }, [speed]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      try {
        await audio.play();
        setIsPlaying(true);
        setPlaybackFailed(false);
      } catch {
        setPlaybackFailed(true);
      }
    } else {
      audio.pause();
      setIsPlaying(false);
    }
  }

  function cycleSpeed() {
    const index = SPEEDS.indexOf(speed);
    onSpeedChange(SPEEDS[(index + 1) % SPEEDS.length]);
  }

  const hasAudio = Boolean(audioUrl) && !playbackFailed;

  return (
    <div className="rounded-xl border-2 border-saral-ink bg-saral-charcoal p-2.5 text-white shadow-[2px_2px_0_0_#0D0D0D]">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={togglePlayback}
          disabled={!hasAudio || isLoading}
          aria-label={isPlaying ? 'Pause the simplified audio' : 'Play the simplified audio'}
          className="focus-ring-light flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-saral-yellow text-saral-ink shadow-[1px_1px_0_0_#000] active:scale-95 disabled:opacity-50"
        >
          {isLoading ? (
            <SpinnerIcon className="text-[16px]" />
          ) : isPlaying ? (
            <PauseIcon className="text-[16px]" />
          ) : (
            <PlayIcon className="text-[16px]" />
          )}
        </button>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center justify-between text-[10px] font-bold text-white/80">
            <span>{formatTime(currentTime)}</span>
            <span className="opacity-70">{duration ? formatTime(duration) : '—'}</span>
          </div>
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={duration ? Math.min(currentTime, duration) : 0}
            disabled={!hasAudio}
            onChange={(event) => {
              const next = Number(event.target.value);
              setCurrentTime(next);
              if (audioRef.current) audioRef.current.currentTime = next;
            }}
            aria-label="Audio position"
            className="h-1.5 w-full cursor-pointer accent-saral-yellow disabled:opacity-40"
          />
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={cycleSpeed}
            aria-label={`Playback speed ${speed} times. Activate to change.`}
            className="focus-ring-light rounded bg-white/15 px-1.5 py-0.5 text-[10px] font-bold hover:bg-white/25"
          >
            {speed.toFixed(2).replace(/0$/, '')}x
          </button>
          <button
            type="button"
            onClick={() => setIsMuted((muted) => !muted)}
            aria-label={isMuted ? 'Unmute audio' : 'Mute audio'}
            className="focus-ring-light rounded p-0.5 hover:bg-white/15"
          >
            <VolumeIcon className="text-[16px]" />
          </button>
        </div>
      </div>

      <div className="mt-1.5 flex items-center gap-2">
        <label htmlFor="saral-volume" className="sr-only">
          Volume
        </label>
        <input
          id="saral-volume"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={isMuted ? 0 : volume}
          onChange={(event) => {
            setIsMuted(false);
            setVolume(Number(event.target.value));
          }}
          className="h-1.5 w-20 cursor-pointer accent-saral-yellow"
        />
        {error ? (
          <span role="alert" className="flex-1 truncate text-[10px] font-bold text-red-300">
            {error}
          </span>
        ) : playbackFailed ? (
          <span role="alert" className="flex-1 truncate text-[10px] font-bold text-amber-300">
            Audio file is no longer available. Generate it again.
          </span>
        ) : null}
      </div>
    </div>
  );
}
