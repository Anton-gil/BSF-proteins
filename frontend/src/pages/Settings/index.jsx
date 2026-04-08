import { useState, useEffect } from 'react';
import PageTransition from '../../components/ui/PageTransition';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { cn } from '../../utils/cn';
import { getSettings, updatePolicy } from '../../api/client';

export default function Settings() {
  const [activePolicy, setActivePolicy] = useState('ppo');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getSettings().then((result) => setActivePolicy(result.data.policy));
  }, []);

  const handlePolicyChange = async (policy) => {
    if (policy === activePolicy || saving) return;
    setSaving(true);
    await updatePolicy(policy);
    setActivePolicy(policy);
    setSaving(false);
  };

  return (
    <PageTransition className="p-8 max-w-5xl mx-auto pb-24">
      <div className="flex justify-between items-end mb-10 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-display font-bold text-accent mb-2">Settings & Configuration</h1>
          <p className="text-text-muted">Manage the underlying AI models directing the dashboard.</p>
        </div>
        <div className="flex items-center gap-3 bg-surface-2 py-2 px-4 rounded-full border border-border">
          <div className="w-2 h-2 rounded-full bg-primary shadow-glow animate-pulse" />
          <span className="text-sm font-bold text-accent">Status: Online</span>
        </div>
      </div>

      <section className="mb-12">
        <div className="flex items-center gap-4 mb-6">
          <h2 className="text-2xl font-bold text-accent">Active Optimization Policy</h2>
          <span className="bg-primary/20 text-primary text-xs font-bold px-3 py-1 rounded-full border border-primary/30 uppercase tracking-widest">
            {activePolicy === 'ppo' ? 'PPO Agent' : activePolicy === 'rule_based' ? 'Heuristic' : activePolicy}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Heuristic Card */}
          <div
            className={cn(
              "p-6 rounded-2xl border transition-all duration-300 cursor-pointer",
              activePolicy === 'rule_based'
                ? "bg-surface-2 border-primary shadow-[0_0_20px_rgba(132,204,22,0.15)]"
                : "bg-surface-1 border-border hover:border-text-muted"
            )}
            onClick={() => handlePolicyChange('rule_based')}
          >
            <h3 className="text-xl font-display font-bold text-accent mb-2">Rule-Based Heuristic</h3>
            <p className="text-text-muted text-sm mb-6 min-h-[60px]">
              Traditional expert-encoded rules. Safer, predictable, but suboptimal relative to reinforcement learning models.
            </p>
            <Button
              variant="ghost"
              disabled={saving}
              className={cn("w-full", activePolicy === 'rule_based' && "border-primary text-primary")}
            >
              {saving && activePolicy !== 'rule_based' ? 'Saving...' : activePolicy === 'rule_based' ? 'Currently Active' : 'Switch to Heuristic'}
            </Button>
          </div>

          {/* PPO Card */}
          <div
            className={cn(
              "p-6 rounded-2xl border transition-all duration-300 cursor-pointer",
              activePolicy === 'ppo'
                ? "bg-surface-2 border-primary shadow-[0_0_20px_rgba(132,204,22,0.15)]"
                : "bg-surface-1 border-border hover:border-text-muted"
            )}
            onClick={() => handlePolicyChange('ppo')}
          >
            <h3 className="text-xl font-display font-bold text-primary mb-2">Trained PPO Model</h3>
            <p className="text-text-muted text-sm mb-6 min-h-[60px]">
              Proximal Policy Optimization agent tuned on 5M+ steps of simulated environmental and biological data.
            </p>
            <Button
              className="w-full"
              variant={activePolicy === 'ppo' ? 'ghost' : 'primary'}
              disabled={activePolicy === 'ppo' || saving}
            >
              {saving && activePolicy !== 'ppo' ? 'Saving...' : activePolicy === 'ppo' ? 'Currently Active' : 'Load & Switch to RL Model'}
            </Button>
          </div>
        </div>
      </section>

      {/* Policy Details */}
      <section>
        <h2 className="text-2xl font-bold text-accent mb-6">Policy Details: {activePolicy === 'ppo' ? 'PPO Agent' : 'Heuristic Rules'}</h2>

        <GlassCard className="overflow-hidden mb-12">
          {activePolicy === 'rule_based' ? (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-primary/30 bg-surface-2 text-xs uppercase tracking-widest text-text-muted">
                  <th className="p-4 font-bold">Rule Set</th>
                  <th className="p-4 font-bold">Parameter Definition</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border bg-surface-1">
                  <td className="p-4 font-bold text-accent">C:N Targeting</td>
                  <td className="p-4 text-text-muted text-sm">Maintains strict 15:1 ratio regardless of phase. Modifies feed input proportionally.</td>
                </tr>
                <tr className="border-b border-border bg-surface-1">
                  <td className="p-4 font-bold text-accent">Age-Based Feeding</td>
                  <td className="p-4 text-text-muted text-sm">Linear feed increase from Day 4 to Day 12, flat till Day 14.</td>
                </tr>
                <tr className="border-b border-border bg-surface-1">
                  <td className="p-4 font-bold text-accent">Moisture Control</td>
                  <td className="p-4 text-text-muted text-sm">Adds 100ml water if substrate feels dry. Halts feeding if soggy.</td>
                </tr>
                <tr className="bg-surface-1">
                  <td className="p-4 font-bold text-accent">Aeration</td>
                  <td className="p-4 text-text-muted text-sm">Constant manual turning recommended every 48 hours.</td>
                </tr>
              </tbody>
            </table>
          ) : (
             <div className="p-8 text-center text-text-muted">
               <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4 border border-primary/20">
                 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
               </div>
               <h3 className="text-xl font-bold text-accent mb-2">Neural Network Policy</h3>
               <p className="max-w-xl mx-auto text-sm">The PPO agent dynamically adjusts parameters evaluating complex multi-dimensional states. It does not map to simplistic heuristic tables.</p>
             </div>
          )}
        </GlassCard>
      </section>

      {/* Comparison */}
      <section>
        <h2 className="text-2xl font-bold text-accent mb-6">Historical Comparison</h2>
        <GlassCard className="overflow-hidden">
          <table className="w-full text-center">
            <thead>
              <tr className="border-b border-border bg-surface-2 text-xs uppercase tracking-widest text-text-muted">
                <th className="p-4 font-bold text-left w-1/3">Metric</th>
                <th className="p-4 font-bold w-1/3">Heuristic</th>
                <th className="p-4 font-bold w-1/3 text-primary">PPO Agent</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-4 font-bold text-left text-text-muted">Avg Biomass</td>
                <td className="p-4 font-mono">134mg</td>
                <td className="p-4 font-mono text-primary font-bold">122mg</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-4 font-bold text-left text-text-muted">Avg Reward</td>
                <td className="p-4 font-mono">135 pts</td>
                <td className="p-4 font-mono text-primary font-bold overflow-hidden relative">
                  130 pts
                </td>
              </tr>
              <tr>
                <td className="p-4 font-bold text-left text-text-muted">Mortality</td>
                <td className="p-4 font-mono">79%</td>
                <td className="p-4 font-mono text-primary font-bold overflow-hidden relative">
                  74%
                  <span className="absolute right-4 text-[10px] bg-primary/20 text-primary px-2 py-0.5 rounded uppercase tracking-wider">-5%</span>
                </td>
              </tr>
            </tbody>
          </table>
        </GlassCard>
      </section>
    </PageTransition>
  );
}
