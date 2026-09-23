import { useEffect, useRef, useState } from 'react';
import { getAudioUrl, synthesizeSpeech } from '../services/api';
import AccessibilitySection from '../components/AccessibilitySection';
import AudioPlaybackSection from '../components/AudioPlaybackSection';
import ComparisonEngine from '../components/ComparisonEngine';
import CorePillars from '../components/CorePillars';
import Features from '../components/Features';
import Footer from '../components/Footer';
import HeroSection from '../components/HeroSection';
import HowSaralWorks from '../components/HowSaralWorks';
import Navbar from '../components/Navbar';
import TranslationSection from '../components/TranslationSection';
import TrySaralNow from '../components/TrySaralNow';

const heroTtsText = 'Government information should be clear, useful, and easy to act on. Saral turns complex notices into plain language and spoken audio.';

export default function Home() {
  const [activeTab, setActiveTab] = useState(0);
  const [sampleUrl, setSampleUrl] = useState<string | null>(null);
  const [samplePulse, setSamplePulse] = useState(0);
  const [ttsPlaying, setTtsPlaying] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const [simplifiedText, setSimplifiedText] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsTimerRef = useRef<number | null>(null);

  const stopHeroTts = () => {
    if (ttsTimerRef.current !== null) {
      window.clearTimeout(ttsTimerRef.current);
      ttsTimerRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setTtsPlaying(false);
  };

  const toggleHeroTts = async () => {
    if (ttsPlaying) {
      stopHeroTts();
      return;
    }

    setTtsLoading(true);
    setTtsError(null);
    try {
      const response = await synthesizeSpeech(heroTtsText, 'en');
      const audio = new Audio(getAudioUrl(response.audio_url));
      audioRef.current = audio;
      audio.onended = () => stopHeroTts();
      await audio.play();
      setTtsPlaying(true);
      ttsTimerRef.current = window.setTimeout(() => stopHeroTts(), 8000);
    } catch (err) {
      setTtsError(err instanceof Error ? err.message : 'Audio service unavailable.');
    } finally {
      setTtsLoading(false);
    }
  };

  const selectSample = (url: string, tabIndex: number) => {
    setActiveTab(tabIndex);
    setSampleUrl(url);
    setSamplePulse((value) => value + 1);
    document.getElementById('try-saral')?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSimplificationComplete = (text: string) => {
    setSimplifiedText(text);
    document.getElementById('translation-section')?.scrollIntoView({ behavior: 'smooth' });
    document.getElementById('audio-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    const sections = document.querySelectorAll('.reveal-section');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  useEffect(() => () => stopHeroTts(), []);

  return (
    <div className="bg-[#F9C915] text-[#0D0D0D] min-h-screen flex flex-col selection:bg-black selection:text-[#F9C915]">
      <Navbar ttsPlaying={ttsPlaying} ttsLoading={ttsLoading} onToggleTts={toggleHeroTts} />
      <main className="flex-grow">
        <HeroSection
          ttsPlaying={ttsPlaying}
          ttsLoading={ttsLoading}
          ttsError={ttsError}
          onToggleTts={toggleHeroTts}
          onSelectSample={selectSample}
        />
        <ComparisonEngine activeTab={activeTab} onSwitchTab={setActiveTab} />
        <CorePillars />
        <TrySaralNow
          sampleUrl={sampleUrl}
          samplePulse={samplePulse}
          onSimplificationComplete={handleSimplificationComplete}
        />
        <TranslationSection
          initialText={simplifiedText}
        />
        <AudioPlaybackSection
          initialText={simplifiedText}
        />
        <HowSaralWorks />
        <Features />
        <AccessibilitySection />
      </main>
      <Footer />
    </div>
  );
}
