import { useEffect, useState } from 'react';
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

export default function Home() {
  const [activeTab, setActiveTab] = useState(0);
  const [sampleUrl, setSampleUrl] = useState<string | null>(null);
  const [samplePulse, setSamplePulse] = useState(0);
  const [simplifiedText, setSimplifiedText] = useState('');

  const selectSample = (url: string, tabIndex: number) => {
    setActiveTab(tabIndex);
    setSampleUrl(url);
    setSamplePulse((value) => value + 1);
    document.getElementById('try-saral')?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSimplificationComplete = (text: string) => {
    setSimplifiedText(text);
    document.getElementById('translation')?.scrollIntoView({ behavior: 'smooth' });
    document.getElementById('audio-playback')?.scrollIntoView({ behavior: 'smooth' });
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

  return (
    <div className="bg-[#F9C915] text-[#0D0D0D] min-h-screen flex flex-col selection:bg-black selection:text-[#F9C915]">
      <Navbar />
      <main className="flex-grow">
        <HeroSection
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