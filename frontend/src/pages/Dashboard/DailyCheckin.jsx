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

  // All waste types from waste_lookup.yaml — grouped by category with C:N info
  const wasteCategories = [
    {
      label: '🐓 High Nitrogen (C:N 3–15) — Best for protein growth',
      items: [
        { id: 'chicken_manure',        label: 'Chicken Manure',         cn: 8  },
        { id: 'fish_waste',            label: 'Fish Waste',             cn: 6  },
        { id: 'fish_meal',             label: 'Fish Meal',              cn: 5  },
        { id: 'blood_meal',            label: 'Blood Meal',             cn: 3  },
        { id: 'shrimp_waste',          label: 'Shrimp Waste',           cn: 7  },
        { id: 'meat_scraps',           label: 'Meat Scraps',            cn: 6  },
        { id: 'egg_waste',             label: 'Egg Waste / Shells',     cn: 5  },
      ]
    },
    {
      label: '⚖️ Balanced (C:N 15–25) — Reliable base feed',
      items: [
        { id: 'rice_bran',             label: 'Rice Bran',              cn: 20 },
        { id: 'wheat_bran',            label: 'Wheat Bran',             cn: 18 },
        { id: 'vegetable_scraps_mixed',label: 'Mixed Vegetable Scraps', cn: 20 },
        { id: 'kitchen_waste_mixed',   label: 'Mixed Kitchen Waste',    cn: 18 },
        { id: 'restaurant_waste',      label: 'Restaurant Waste',       cn: 15 },
        { id: 'tofu_waste',            label: 'Tofu Waste / Okara',     cn: 12 },
        { id: 'brewery_waste',         label: 'Brewery / Spent Grain',  cn: 15 },
        { id: 'coffee_grounds',        label: 'Coffee Grounds',         cn: 22 },
      ]
    },
    {
      label: '🍌 Moderate Carbon (C:N 25–40) — Needs nitrogen supplement',
      items: [
        { id: 'banana_peels',          label: 'Banana Peels',           cn: 30 },
        { id: 'mango_waste',           label: 'Mango Waste',            cn: 35 },
        { id: 'papaya_waste',          label: 'Papaya Waste',           cn: 32 },
        { id: 'watermelon_rind',       label: 'Watermelon Rind',        cn: 30 },
        { id: 'pineapple_waste',       label: 'Pineapple Waste',        cn: 35 },
        { id: 'orange_peels',          label: 'Orange Peels',           cn: 35 },
        { id: 'apple_pomace',          label: 'Apple Pomace',           cn: 30 },
        { id: 'bread_waste',           label: 'Bread Waste',            cn: 25 },
        { id: 'cooked_rice',           label: 'Cooked Rice (leftover)', cn: 35 },
        { id: 'potato_waste',          label: 'Potato Waste',           cn: 28 },
        { id: 'carrot_waste',          label: 'Carrot Waste',           cn: 27 },
        { id: 'cabbage_waste',         label: 'Cabbage Waste',          cn: 25 },
        { id: 'coconut_meat',          label: 'Coconut Meat Waste',     cn: 40 },
      ]
    },
    {
      label: '🌾 High Carbon (C:N > 40) — Bulking agents only',
      items: [
        { id: 'rice_straw',            label: 'Rice Straw',             cn: 70  },
        { id: 'coconut_coir',          label: 'Coconut Coir',           cn: 80  },
        { id: 'sugarcane_bagasse',     label: 'Sugarcane Bagasse',      cn: 100 },
        { id: 'corn_stover',           label: 'Corn Stover',            cn: 60  },
      ]
    },
  ];

  // Flat list for lookup
  const allWasteItems = wasteCategories.flatMap(c => c.items);

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
                <p className="text-text">
                  {status === 'Active & healthy'
                    ? 'Good to hear! What waste is available to feed them today?'
                    : status === 'A few deaths'
                    ? 'Noted — some mortality is normal at this stage. What waste do you have available today?'
                    : status === 'Many deaths'
                    ? 'That\'s concerning. Let\'s get you the right feeding plan — what waste is available today?'
                    : 'Understood. What waste is available to feed them today?'}
                </p>
              </div>

              {step === 2 && (
                <GlassCard className="p-6 self-end w-[90%] border-primary/30">

                  {/* Live C:N blended display */}
                  {Object.keys(waste).length > 0 && (() => {
                    const entries = Object.entries(waste);
                    const totalKg = entries.reduce((s, [, kg]) => s + kg, 0);
                    const blendedCN = totalKg > 0
                      ? entries.reduce((s, [id, kg]) => {
                          const item = allWasteItems.find(w => w.id === id);
                          return s + (item?.cn || 20) * kg;
                        }, 0) / totalKg
                      : 0;
                    const cnColor = blendedCN >= 14 && blendedCN <= 18 ? 'text-primary' : (blendedCN >= 10 && blendedCN <= 30) ? 'text-yellow-400' : 'text-red-400';
                    return (
                      <div className="mb-4 p-3 rounded-lg bg-surface-2 border border-border flex justify-between items-center text-sm">
                        <span className="text-text-muted">Blended C:N Ratio</span>
                        <span className={`font-bold text-lg ${cnColor}`}>
                          {blendedCN.toFixed(1)}:1
                          {blendedCN >= 14 && blendedCN <= 18 && ' ✅ Optimal'}
                          {((blendedCN >= 10 && blendedCN < 14) || (blendedCN > 18 && blendedCN <= 30)) && ' ⚠️ Acceptable'}
                          {(blendedCN < 10 || blendedCN > 30) && ' ❌ Poor'}
                        </span>
                      </div>
                    );
                  })()}

                  {/* Grouped waste categories */}
                  <div className="space-y-5 mb-6 max-h-80 overflow-y-auto pr-1">
                    {wasteCategories.map((cat) => (
                      <div key={cat.label}>
                        <p className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">{cat.label}</p>
                        <div className="flex flex-wrap gap-2">
                          {cat.items.map(({ id, label, cn }) => {
                            const isActive = waste[id] !== undefined;
                            return (
                              <button
                                key={id}
                                onClick={() => handleWasteSelect(id)}
                                className={
                                  "px-3 py-1.5 rounded-lg text-sm border transition-colors flex items-center gap-1.5 " +
                                  (isActive
                                    ? "bg-primary/20 border-primary text-primary font-medium"
                                    : "bg-transparent border-border text-text-muted hover:border-primary/50")
                                }
                              >
                                {label}
                                <span className="text-[10px] opacity-60 font-mono">{cn}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Quantity inputs */}
                  {Object.keys(waste).length > 0 && (
                    <div className="space-y-3 mb-6">
                      <p className="text-xs font-bold text-text-muted uppercase tracking-wider">Quantities (kg)</p>
                      {Object.keys(waste).map((id) => {
                        const item = allWasteItems.find(w => w.id === id);
                        return (
                          <div key={id} className="flex justify-between items-center bg-surface-2 p-2 rounded border border-border">
                            <span className="text-sm">{item?.label || id}</span>
                            <input
                              type="number"
                              value={waste[id]}
                              onChange={(e) => handleUpdateQuantity(id, e.target.value)}
                              className="bg-bg border border-border rounded w-20 text-center text-sm py-1 focus:outline-none focus:border-primary"
                            />
                          </div>
                        );
                      })}
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

              {/* Target C:N + Confidence row */}
              {apiResult && (
                <div className="flex flex-wrap gap-3 w-full self-end">
                  <div className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm">
                    <span className="text-text-muted">Target C:N:</span>
                    <span className="font-bold text-primary">{apiResult.target_cn?.toFixed(1)}:1</span>
                  </div>
                  <div className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm">
                    <span className="text-text-muted">Confidence:</span>
                    <span className="font-bold text-primary">{Math.round((apiResult.confidence ?? 0) * 100)}%</span>
                  </div>
                  <div className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm">
                    <span className="text-text-muted">Moisture:</span>
                    <span className="font-bold text-cyan-400">{apiResult.moisture_action}</span>
                  </div>
                  <div className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm">
                    <span className="text-text-muted">Aeration:</span>
                    <span className="font-bold text-cyan-400">{apiResult.aeration_action}</span>
                  </div>
                </div>
              )}

              {/* LLM Coach Message */}
              {apiResult?.coach_message && (
                <div className="w-full self-end bg-primary/5 border border-primary/25 rounded-xl p-4 text-sm text-text leading-relaxed">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-primary text-xs font-bold uppercase tracking-wider">AI Coach</span>
                    <span className="text-[10px] text-text-muted bg-surface-2 px-2 py-0.5 rounded-full">local model</span>
                  </div>
                  <p className="text-text-muted">{apiResult.coach_message}</p>
                </div>
              )}

              {/* Notes from AI */}
              {apiResult?.notes?.length > 0 && (
                <div className="w-full self-end bg-yellow-400/10 border border-yellow-400/30 rounded-lg p-3 text-sm text-yellow-300">
                  <span className="font-bold">⚠️ Notes: </span>
                  {apiResult.notes.join(' • ')}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full self-end mt-2">
                {(apiResult?.schedule ?? []).map((feeding, i) => (
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
                  <div className="text-sm font-bold">Harvest-Day Biomass Projection</div>
                  <div className="text-xs text-text-muted mt-1">
                    Expected at Day 16: <span className="text-primary font-bold">{apiResult?.projection?.expected ?? '—'} mg</span>
                    {' '}• Trajectory: <span className="text-primary font-bold">{apiResult?.projection?.trajectory ?? '—'}</span>
                  </div>
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
