import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';

export default function DailyCheckin() {
  const [step, setStep] = useState(1);
  const [status, setStatus] = useState(null);
  const [waste, setWaste] = useState({});
  const [isCalculating, setIsCalculating] = useState(false);

  // Mock waste types
  const wasteTypes = [
    "Vegetable Scraps", "Fruit Waste", "Bakery Waste", 
    "Spent Grain", "Coffee Grounds", "Manure"
  ];

  const handleWasteSelect = (type) => {
    if (waste[type] !== undefined) {
      const newWaste = { ...waste };
      delete newWaste[type];
      setWaste(newWaste);
    } else {
      setWaste({ ...waste, [type]: 5 }); // Default 5kg
    }
  };

  const handleUpdateQuantity = (type, val) => {
    setWaste({ ...waste, [type]: parseInt(val) || 0 });
  };

  const handleSubmit = () => {
    setIsCalculating(true);
    setStep(3);
    setTimeout(() => {
      setIsCalculating(false);
      setStep(4);
    }, 2000);
  };

  return (
    <div className="p-8 max-w-3xl mx-auto pb-24">
      <h1 className="text-3xl font-display font-bold text-accent mb-8">Daily Check-in</h1>
      
      <div className="space-y-8">
        
        {/* Step 1: Status */}
        <AnimatePresence>
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-start gap-4"
          >
            <div className="bg-surface-2 p-4 rounded-2xl rounded-tl-none border border-border max-w-[80%]">
              <p className="text-text">Hi! It's Day 8 for Batch #204. How are your larvae looking today?</p>
            </div>
            
            {(step === 1 || status) && (
              <div className="flex flex-wrap gap-3 self-end justify-end max-w-[80%]">
                {['Active & healthy', 'A few deaths', 'Many deaths', 'Looking sick'].map((opt) => {
                  let cls = "px-4 py-2 rounded-full text-sm font-medium transition-all ";
                  if (status === opt) {
                    cls += "bg-primary text-[#050a05] shadow-glow";
                  } else if (step === 1) {
                    cls += "bg-surface-2 border border-border text-text hover:border-primary/50";
                  } else {
                    cls += "hidden";
                  }
                  
                  return (
                    <button
                      key={opt}
                      onClick={() => { setStatus(opt); setStep(2); }}
                      disabled={step > 2 && status !== opt}
                      className={cls}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Step 2: Waste */}
        <AnimatePresence>
          {step >= 2 && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-start gap-4"
            >
              <div className="bg-surface-2 p-4 rounded-2xl rounded-tl-none border border-border max-w-[80%]">
                <p className="text-text">Great. What waste is available to feed them today?</p>
              </div>

              {step === 2 && (
                <GlassCard className="p-6 self-end w-[90%] border-primary/30">
                  <div className="flex flex-wrap gap-2 mb-6">
                    {wasteTypes.map((type) => {
                      const isActive = waste[type] !== undefined;
                      const cls = "px-3 py-1.5 rounded-lg text-sm border transition-colors " +
                        (isActive 
                          ? "bg-primary/20 border-primary text-primary font-medium"
                          : "bg-transparent border-border text-text-muted hover:border-primary/50");
                      return (
                        <button
                          key={type}
                          onClick={() => handleWasteSelect(type)}
                          className={cls}
                        >
                          {type}
                        </button>
                      );
                    })}
                  </div>

                  {Object.keys(waste).length > 0 && (
                    <div className="space-y-3 mb-6">
                      <p className="text-xs font-bold text-text-muted uppercase tracking-wider">Quantities (kg)</p>
                      {Object.keys(waste).map((type) => (
                        <div key={type} className="flex justify-between items-center bg-surface-2 p-2 rounded border border-border">
                          <span className="text-sm">{type}</span>
                          <input 
                            type="number"
                            value={waste[type]}
                            onChange={(e) => handleUpdateQuantity(type, e.target.value)}
                            className="bg-bg border border-border rounded w-20 text-center text-sm py-1 focus:outline-none focus:border-primary"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  <Button 
                    onClick={handleSubmit} 
                    disabled={Object.keys(waste).length === 0}
                    className="w-full"
                  >
                    Calculate Optimal Schedule
                  </Button>
                </GlassCard>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Step 3: Calculating */}
        <AnimatePresence>
          {step >= 3 && isCalculating && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-4 bg-surface-2 p-4 rounded-2xl rounded-tl-none border border-border w-fit"
            >
              <div className="w-5 h-5 border-2 border-border border-t-primary rounded-full animate-spin" />
              <p className="text-text text-sm">PPO Agent computing C:N targets...</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Step 4: Output / Schedule */}
        <AnimatePresence>
          {step === 4 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-start gap-4"
            >
              <div className="bg-primary/10 p-4 rounded-2xl rounded-tl-none border border-primary/30 max-w-[80%]">
                <p className="text-primary font-medium">Here is your optimal schedule for the day.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full self-end mt-4">
                {[
                  { time: '08:00 AM', mix: '2kg Veg + 1kg Bakery', h2o: '+500ml H2O' },
                  { time: '02:00 PM', mix: '3kg Fruit', h2o: 'No added water' },
                  { time: '06:00 PM', mix: '1kg Spent Grain', h2o: '+200ml H2O' }
                ].map((feeding, i) => (
                  <GlassCard key={i} className="p-5 relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-primary/50 group-hover:bg-primary transition-colors" />
                    <div className="text-xl font-display font-bold text-accent mb-1">{feeding.time}</div>
                    <div className="text-text text-sm mb-3">{feeding.mix}</div>
                    <div className="text-xs font-medium text-cyan-400 bg-cyan-400/10 inline-block px-2 py-1 rounded">
                      {feeding.h2o}
                    </div>
                  </GlassCard>
                ))}
              </div>
              
              <div className="w-full mt-4 p-4 rounded-lg bg-surface-2 border border-border flex justify-between items-center">
                <div>
                  <div className="text-sm font-bold">Tomorrow's Projection</div>
                  <div className="text-xs text-text-muted mt-1">Expected Biomass: <span className="text-primary font-bold">48mg</span> • Trajectory: <span className="text-primary font-bold">Optimal</span></div>
                </div>
                <Button variant="ghost">Complete Check-in</Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
