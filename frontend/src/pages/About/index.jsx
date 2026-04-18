import PageTransition from '../../components/ui/PageTransition';
import FrameScroller from './FrameScroller';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';

export default function About() {
  const biologyFacts = [
    { title: "Ideal C:N Ratio", value: "15:1 to 25:1", desc: "Carbon-to-Nitrogen ratio dictates growth efficiency and dictates AI formulation." },
    { title: "Temperature Range", value: "27°C - 30°C", desc: "Optimal environmental temperature for exponential phase." },
    { title: "Moisture Content", value: "60% - 70%", desc: "Substrate moisture levels must be maintained through calculated additions." },
    { title: "Lifecycle Duration", value: "12 - 18 days", desc: "From neonate to prepupa, depending on feed quality and environmental factors." },
    { title: "Feed Conversion", value: "~1.5 - 2.0", desc: "Kilograms of dry waste required to produce 1 kg of wet larval biomass." },
    { title: "Waste Reduction", value: "Up to 70%", desc: "Volume reduction capability on pure organic waste streams." }
  ];

  return (
    <PageTransition>
      <main className="w-full min-h-screen">
        {/* Intro Hero */}
        <section className="pt-24 pb-12 text-center px-6">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-6xl font-display font-bold text-accent mb-4"
          >
            The <span className="text-primary italic">Biology</span> Behind the AI
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-text-muted max-w-2xl mx-auto"
          >
            Black Soldier Flies are hyper-efficient organic recyclers. Scroll to see their 16-day trajectory.
          </motion.p>
        </section>

        {/* Feature Section */}
        <FrameScroller />

        {/* Facts Section */}
        <section className="py-24 bg-surface-2 border-t border-border">
          <div className="container mx-auto px-6 max-w-5xl">
            <h2 className="text-3xl font-display font-bold text-center mb-12">Biology Quick Facts</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {biologyFacts.map((fact, i) => (
                <GlassCard key={i} className="p-6">
                  <h3 className="text-sm uppercase tracking-widest text-text-muted mb-2 font-bold">{fact.title}</h3>
                  <div className="text-2xl font-display font-bold text-primary mb-3">{fact.value}</div>
                  <p className="text-sm text-text-muted/80">{fact.desc}</p>
                </GlassCard>
              ))}
            </div>
          </div>
        </section>

        {/* Vision & AI Approach Section */}
        <section className="py-24">
          <div className="container mx-auto px-6 max-w-4xl text-center">
            <h2 className="text-3xl font-display font-bold mb-8 text-accent">What We Are Building</h2>
            <div className="space-y-6 text-text-muted text-lg leading-relaxed text-left bg-surface-2 p-8 rounded-2xl border border-border">
              <p>
                Our vision is to revolutionize the way insect farming is conducted by moving away from traditional, rigid rule-based heuristics to highly adaptive, intelligent systems. 
                <strong className="text-primary"> The Black Soldier Fly (Hermetia illucens)</strong> is nature's ultimate upcycler, capable of transforming organic waste into high-quality protein and lipids. However, maximizing their growth while minimizing feed usage and mortality requires perfectly timed micro-adjustments to environmental conditions and feed formulations.
              </p>
              <p>
                Through the power of a custom <strong className="text-accent">Proximal Policy Optimization (PPO) Reinforcement Learning Agent</strong>, our platform actively monitors the biomass, ambient temperature, humidity, and C:N (Carbon to Nitrogen) ratio of the substrate in real-time. Instead of following a static feeding schedule, the AI dynamically learns the optimal moments to intervene, effectively 'learning' the insect's biology on a granular scale.
              </p>
              <p>
                As we continue to develop this platform, we plan to integrate advanced computer vision for live larvae counting, automated IoT dispenser controls for hands-free facility management, and multi-agent coordination for optimizing entire industrial warehouses simultaneously. The future of sustainable protein is AI-driven, and it starts here.
              </p>
            </div>
          </div>
        </section>
      </main>
    </PageTransition>
  );
}
