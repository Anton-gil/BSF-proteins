import PageTransition from '../../components/ui/PageTransition';
import HeroSection from './HeroSection';
import StatsBar from './StatsBar';
import TimelineSection from './TimelineSection';
import AIvsHuman from './AIvsHuman';

export default function Landing() {
  return (
    <PageTransition>
      <main className="w-full flex flex-col min-h-screen">
        <HeroSection />
        <StatsBar />
        <TimelineSection />
        <AIvsHuman />
      </main>
    </PageTransition>
  );
}
