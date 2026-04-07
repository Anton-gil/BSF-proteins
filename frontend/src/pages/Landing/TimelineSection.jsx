import { motion } from 'framer-motion';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import { cn } from '../../utils/cn';
import GlassCard from '../../components/ui/GlassCard';

export default function TimelineSection() {
  const { ref, isInView } = useScrollAnimation("-10%");

  // Generate 17 days (0 to 16)
  const days = Array.from({ length: 17 }, (_, i) => {
    let stage = '';
    let action = '';
    let colorClass = '';
    
    if (i <= 4) {
      stage = i <= 2 ? 'Egg Stage' : 'Neonate';
      action = 'Minimal feeding, establish baseline moisture.';
      colorClass = 'text-primary/50 border-primary/50';
    } else if (i <= 11) {
      stage = i <= 7 ? 'Early Growth' : 'Exponential Growth';
      action = 'OPTIMIZE: Heavy C:N targeting. Maximize daily feed limit.';
      colorClass = 'text-primary-bright border-primary-bright glow-primary';
    } else {
      stage = i <= 14 ? 'Late Growth' : 'Pre-Pupa';
      action = 'Reduce moisture, prepare for harvest. Cease feeding.';
      colorClass = 'text-amber-500 border-amber-500';
    }

    return { day: i, stage, action, colorClass, isOptimal: i >= 5 && i <= 11 };
  });

  return (
    <section ref={ref} className="py-24 bg-surface-2 relative border-y border-border">
      <div className="container mx-auto px-6 mb-12 text-center">
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          className="text-3xl md:text-5xl font-display font-bold mb-4"
        >
          16-Day Lifecycle Target
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : { opacity: 0 }}
          transition={{ delay: 0.2 }}
          className="text-text-muted"
        >
          Reinforcement learning agent optimizes feeding across the entire growth phase.
        </motion.p>
      </div>

      {/* Horizontal Scroll Area */}
      <motion.div 
        initial={{ opacity: 0, x: 50 }}
        animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 50 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="w-full overflow-x-auto pb-12 snap-x snap-mandatory hide-scroll focus:outline-none"
      >
        {/* Adds padding to sides so it doesn't touch the very edge initially */}
        <div className="flex w-max px-6 md:px-24 gap-4 pb-8 min-h-[200px] items-center">
          {days.map((d) => (
            <div key={d.day} className="relative snap-center group flex flex-col items-center shrink-0 w-32">
              {/* Connecting line */}
              {d.day < 16 && (
                <div className="absolute top-10 left-1/2 w-full h-[2px] bg-border -z-10" />
              )}
              
              {/* Highlight background for optimal phase */}
              {d.isOptimal && (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-48 bg-primary/5 rounded-2xl -z-20 border border-primary/10" />
              )}

              {/* Day Node */}
              <div className={cn(
                "w-20 h-20 rounded-full flex flex-col items-center justify-center bg-surface-1 border-2 mb-4 transition-all duration-300 group-hover:-translate-y-2",
                d.colorClass,
                d.isOptimal && "shadow-[0_0_15px_rgba(132,204,22,0.3)] bg-surface-2"
              )}>
                <span className="text-xs uppercase font-bold opacity-70">Day</span>
                <span className="text-2xl font-display font-bold leading-none">{d.day}</span>
              </div>
              
              <div className="text-center opacity-80 group-hover:opacity-100 transition-opacity">
                <div className={cn("text-sm font-bold mb-1", d.colorClass.split(' ')[0])}>{d.stage}</div>
              </div>

              {/* Tooltip on hover */}
              <GlassCard className="absolute top-full mt-4 w-48 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none scale-95 group-hover:scale-100 p-3 z-20 origin-top">
                <p className="text-xs text-text-muted leading-tight">{d.action}</p>
              </GlassCard>
            </div>
          ))}
        </div>
      </motion.div>
      
      <style dangerouslySetInnerHTML={{__html: `
        .hide-scroll::-webkit-scrollbar { display: none; }
        .hide-scroll { -ms-overflow-style: none; scrollbar-width: none; }
      `}} />
    </section>
  );
}
