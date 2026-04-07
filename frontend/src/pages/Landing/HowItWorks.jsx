import { motion } from 'framer-motion';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import GlassCard from '../../components/ui/GlassCard';
import { Database, Cpu, CalendarClock } from 'lucide-react';

export default function HowItWorks() {
  const { ref, isInView } = useScrollAnimation("-15%");

  const steps = [
    {
      icon: Database,
      title: "Tell Us Your Waste",
      desc: "You report what organic waste is available for the day.",
    },
    {
      icon: Cpu,
      title: "AI Calculates Optimal Mix",
      desc: "RL model computes exact C:N targets for maximum yield.",
    },
    {
      icon: CalendarClock,
      title: "Get Feeding Schedule",
      desc: "Exact times, amounts, and waste types provided directly.",
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.2 },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, x: -30 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: "easeOut" } },
  };

  return (
    <section ref={ref} className="py-24 relative overflow-hidden">
      <div className="container mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
            transition={{ duration: 0.5 }}
            className="text-3xl md:text-5xl font-display font-bold mb-4"
          >
            How It Works
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-text-muted max-w-xl mx-auto"
          >
            A simple three-step process to optimize your larval growth engine.
          </motion.p>
        </div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="flex flex-col md:flex-row gap-8 max-w-5xl mx-auto"
        >
          {steps.map((step, index) => (
            <motion.div key={index} variants={cardVariants} className="flex-1">
              <GlassCard className="h-full p-8 flex flex-col items-center text-center group">
                <div className="w-16 h-16 rounded-full border border-primary/40 bg-surface-2 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-primary/10 transition-all duration-300">
                  <step.icon className="w-8 h-8 text-primary" />
                </div>
                <div className="text-primary font-display font-bold text-lg mb-2">Step {index + 1}</div>
                <h3 className="text-xl font-bold text-accent mb-3">{step.title}</h3>
                <p className="text-text-muted text-sm leading-relaxed">{step.desc}</p>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
