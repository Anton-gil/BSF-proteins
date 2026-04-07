import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { submitCheckin, saveCheckin } from '../../api/client';
import { useBatchStore, getStageInfo } from '../../store/batchStore';

export default function DailyCheckin() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [status, setStatus] = useState(null);
  const [waste, setWaste] = useState({});
  const [isCalculating, setIsCalculating] = useState(false);
  const [apiResult, setApiResult] = useState(null);
  const [dayCompleted, setDayCompleted] = useState(false);

  const {
    activeBatch,
    currentDay,
    completeDay,
    endBatch,
    setTodaySchedule,
  } = useBatchStore();

  // Guard: no active batch → redirect to start
  if (!activeBatch) {
    return (
      <div className="p-8 max-w-3xl mx-auto pb-24">
        <h1 className="text-3xl font-display font-bold text-accent mb-4">Daily Check-in</h1>
        <GlassCard className="p-8 text-center">
          <p className="text-text-muted text-lg mb-6">No active batch found. Start a new batch first.</p>
          <Button onClick={() => navigate('/dashboard/new')}>Start New Batch</Button>
        </GlassCard>
      </div>
    );
  }

  const stage = getStageInfo(currentDay);
  const batchId = activeBatch.id;
  const larvaeCount = activeBatch.larvaeCount || 10000;

  // Waste types
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
      setWaste({ ...waste, [type]: 5 });
    }
  };

  const handleUpdateQuantity = (type, val) => {
    setWaste({ ...waste, [type]: parseInt(val) || 0 });
  };

  const handleSubmit = async () => {
    setIsCalculating(true);
    setStep(3);
    const payload = {
      batch_id: batchId,
      larvae_activity: status === 'Active & healthy' ? 'very_active' : status === 'A few deaths' ? 'normal' : 'sluggish',
      mortality_estimate: status === 'Active & healthy' ? 'none' : status === 'A few deaths' ? 'few' : status === 'Many deaths' ? 'many' : 'some',
      substrate_condition: 'good',
      smell: 'normal',
      waste_available: waste,
      estimated_larvae_count: larvaeCount,
      age_days: currentDay
    };
    const result = await submitCheckin(payload);
    setApiResult(result.data);
    setTodaySchedule(result.data);
    setIsCalculating(false);
    setStep(4);
  };

  const handleCompleteCheckin = async () => {
    // Calculate total feed from waste
    const totalFeedKg = Object.values(waste).reduce((sum, kg) => sum + kg, 0);

    // Save to backend
    await saveCheckin(batchId, {
      day: currentDay,
      feed_kg: totalFeedKg,
      recommendation: apiResult?.feed_instruction || apiResult?.schedule?.[0]?.mix || 'AI Schedule',
      confirmed_at: new Date().toISOString(),
    });

    // Save to local store
    completeDay({
      day: currentDay,
      feedKg: totalFeedKg,
      recommendation: apiResult?.feed_instruction || apiResult?.schedule?.[0]?.mix || 'AI Schedule',
      schedule: apiResult?.schedule || [],
      status: status,
      confirmedAt: new Date().toISOString(),
    });

    // Check if batch is done (day 15 = last day, 0-indexed)
    if (currentDay >= 15) {
      endBatch();
      navigate('/dashboard/history');
      return;
    }

    // Reset for next day
    setDayCompleted(true);
  };

  const handleNextDay = () => {
    setStep(1);
    setStatus(null);
    setWaste({});
    setApiResult(null);
    setDayCompleted(false);
  };

  // Day completed confirmation screen
  if (dayCompleted) {
    const nextStage = getStageInfo(currentDay); // currentDay was already incremented by completeDay
    return (
      <div className="p-8 max-w-3xl mx-auto pb-24">
        <h1 className="text-3xl font-display font-bold text-accent mb-8">Daily Check-in</h1>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <GlassCard className="p-10">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-accent mb-2">
              Day {currentDay - 1} Complete!
            </h2>
            <p className="text-text-muted mb-6">
              Your larvae are on track. Come back for Day {currentDay} check-in.
            </p>

            <div className="bg-surface-2 rounded-lg p-4 mb-6 inline-block">
              <span className="text-2xl mr-2">{nextStage.emoji}</span>
              <span className="text-primary font-bold">{nextStage.name}</span>
              <span className="text-text-muted ml-2">· Focus: {nextStage.focus}</span>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-surface-2 rounded-full h-3 mb-2 mt-4">
              <div
                className="bg-primary rounded-full h-3 transition-all duration-500"
                style={{ width: `${(currentDay / 16) * 100}%` }}
              />
            </div>
            <p className="text-xs text-text-muted mb-8">Day {currentDay} / 16</p>

            <Button onClick={handleNextDay} className="px-8">
              Start Day {currentDay} Check-in →
            </Button>
          </GlassCard>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto pb-24">
      <h1 className="text-3xl font-display font-bold text-accent mb-2">Daily Check-in</h1>

      {/* Day + Stage banner */}
      <div className="flex items-center gap-3 mb-8">
        <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-bold">
          Day {currentDay}
        </span>
        <span className="text-text-muted text-sm">
          {stage.emoji} {stage.name} · Focus: {stage.focus}
        </span>
        <span className="text-text-muted text-xs ml-auto">
          Batch #{batchId.slice(-4)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-surface-2 rounded-full h-2 mb-8">
        <div
          className="bg-primary rounded-full h-2 transition-all duration-500"
          style={{ width: `${(currentDay / 16) * 100}%` }}
        />
      </div>

      <div className="space-y-8">

        {/* Step 1: Status */}
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-start gap-4"
          >
            <div className="bg-surface-2 p-4 rounded-2xl rounded-tl-none border border-border max-w-[80%]">
              <p className="text-text">Hi! It's Day {currentDay} for Batch #{batchId.slice(-4)}. How are your larvae looking today?</p>
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
                <p className="text-primary font-medium">Here is your optimal schedule for Day {currentDay}.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full self-end mt-4">
                {(apiResult?.schedule ?? [
                  { time: '08:00 AM', mix: '2kg Veg + 1kg Bakery', h2o: '+500ml H2O' },
                  { time: '02:00 PM', mix: '3kg Fruit', h2o: 'No added water' },
                  { time: '06:00 PM', mix: '1kg Spent Grain', h2o: '+200ml H2O' }
                ]).map((feeding, i) => (
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
                  <div className="text-xs text-text-muted mt-1">Expected Biomass: <span className="text-primary font-bold">{apiResult?.projection?.expected ?? '48mg'}</span> • Trajectory: <span className="text-primary font-bold">{apiResult?.projection?.trajectory ?? 'Optimal'}</span></div>
                </div>
                <Button onClick={handleCompleteCheckin}>
                  {currentDay >= 15 ? '🎉 Complete Batch' : '✅ Complete Check-in'}
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
