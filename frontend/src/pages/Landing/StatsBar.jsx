import { motion } from 'framer-motion';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import StatTicker from '../../components/ui/StatTicker';

export default function StatsBar() {
  const { ref, isInView } = useScrollAnimation("-10%");

  const stats = [
    { label: "Avg Biomass (PPO)", value: 148, suffix: " mg" },
    { label: "Avg Reward Score", value: 89, suffix: " pts" },
    { label: "Mortality Reduction vs Baseline", value: 11, suffix: "%" },
    { label: "Avg Batch Duration", value: 16, suffix: " days" },
  ];

  return (
    <section ref={ref} className="w-full bg-surface-2 border-y border-primary/20 py-12 relative z-10">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              transition={{ delay: index * 0.1, duration: 0.6 }}
              className="flex flex-col items-center text-center"
            >
              <div className="text-4xl md:text-5xl font-display font-bold text-primary mb-2 shadow-primary/10 drop-shadow-lg">
                {isInView ? <StatTicker value={stat.value} suffix={stat.suffix} /> : "0" + stat.suffix}
              </div>
              <p className="text-sm md:text-base text-text-muted font-medium uppercase tracking-wider">
                {stat.label}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
