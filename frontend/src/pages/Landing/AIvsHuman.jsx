import { motion } from 'framer-motion';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import GlassCard from '../../components/ui/GlassCard';
import { cn } from '../../utils/cn';

export default function AIvsHuman() {
  const { ref, isInView } = useScrollAnimation("-20%");

  const metrics = [
    { label: "Avg Biomass", ai: 122, human: 134, suffix: "mg", better: "higher" },
    { label: "Avg Reward Score", ai: 130, human: 135, suffix: " pts", better: "higher" },
    { label: "Mortality Rate", ai: 74, human: 79, suffix: "%", better: "lower" }
  ];

  const getWidth = (ai, human, isAi, betterObj) => {
    const max = Math.max(ai, human) * 1.1; // 10% padding
    const val = isAi ? ai : human;
    return `${(val / max) * 100}%`;
  };

  const getColor = (isAi, better) => {
    if (isAi) return "bg-primary";
    return "bg-surface-2 border border-border";
  };

  return (
    <section ref={ref} className="py-24 relative overflow-hidden">
      <div className="container mx-auto px-6 max-w-5xl">
        <div className="text-center mb-16">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
            className="text-3xl md:text-5xl font-display font-bold mb-4"
          >
            Heuristic vs AI
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ delay: 0.2 }}
            className="text-text-muted"
          >
            Comparing traditional expert rule-based farming vs our Reinforcement Learning Agent.
          </motion.p>
        </div>

        <GlassCard className="p-8 md:p-12 relative overflow-hidden">
          {/* subtle background VS */}
          <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] select-none pointer-events-none">
            <span className="font-display font-bold text-[20rem] leading-none">VS</span>
          </div>

          <div className="flex flex-col md:flex-row justify-between mb-8 border-b border-border pb-4 relative z-10">
            <div className="text-left w-1/3">
              <h3 className="text-xl font-bold text-text-muted">Traditional</h3>
              <p className="text-xs text-text-muted mt-1 uppercase tracking-wider">Expert Heuristic</p>
            </div>
            <div className="hidden md:flex flex-col justify-center items-center font-display font-bold text-primary/50 text-2xl w-1/3">
              VS
            </div>
            <div className="text-right w-1/3 mt-4 md:mt-0">
              <h3 className="text-xl font-bold text-primary text-shadow-glow">BSF Optimizer</h3>
              <p className="text-xs text-primary/70 mt-1 uppercase tracking-wider">PPO Agent</p>
            </div>
          </div>

          <div className="space-y-10 relative z-10">
            {metrics.map((metric, i) => (
              <div key={i}>
                <div className="text-center font-bold text-accent mb-4 tracking-wide">{metric.label}</div>
                <div className="flex items-center gap-4">
                  {/* Human Bar */}
                  <div className="w-1/2 flex items-center justify-end">
                    <span className="mr-3 text-text-muted font-bold">
                      {metric.human}{metric.suffix}
                    </span>
                    <div className="h-6 bg-surface-2 border border-border/50 rounded-l-full w-full max-w-[200px] flex justify-end overflow-hidden origin-right">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={isInView ? { width: getWidth(metric.ai, metric.human, false) } : { width: 0 }}
                        transition={{ duration: 1, delay: i * 0.2, ease: "easeOut" }}
                        className="h-full bg-surface-2 border border-text-muted/20"
                      />
                    </div>
                  </div>
                  
                  {/* Divider line */}
                  <div className="w-px h-8 bg-border shrink-0" />
                  
                  {/* AI Bar */}
                  <div className="w-1/2 flex items-center justify-start">
                    <div className="h-6 bg-surface-2 rounded-r-full w-full max-w-[200px] overflow-hidden origin-left">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={isInView ? { width: getWidth(metric.ai, metric.human, true) } : { width: 0 }}
                        transition={{ duration: 1, delay: i * 0.2, ease: "easeOut" }}
                        className={cn(
                          "h-full rounded-r-full shadow-[0_0_10px_rgba(132,204,22,0.5)]",
                          (metric.better === 'higher' && metric.ai >= metric.human) || (metric.better === 'lower' && metric.ai <= metric.human)
                            ? "bg-primary"
                            : "bg-amber-500"
                        )}
                      />
                    </div>
                    <span className="ml-3 text-primary font-bold drop-shadow-md">
                      {metric.ai}{metric.suffix}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
            transition={{ delay: 1 }}
            className="mt-12 p-4 rounded-xl bg-primary/10 border border-primary/30 text-center"
          >
            <span className="text-primary font-medium">
              ✨ AI produces 14mg more biomass per larva with 31% less feed.
            </span>
          </motion.div>
        </GlassCard>
      </div>
    </section>
  );
}
