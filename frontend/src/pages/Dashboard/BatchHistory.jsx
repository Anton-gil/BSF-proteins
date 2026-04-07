import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import GlassCard from '../../components/ui/GlassCard';
import Badge from '../../components/ui/Badge';
import { ChevronDown, Search } from 'lucide-react';
import { getBatches } from '../../api/client';
import { useBatchStore } from '../../store/batchStore';

export default function BatchHistory() {
  const navigate = useNavigate();
  const [expandedRow, setExpandedRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const { batches, setBatches, activeBatch, setActiveBatch, currentDay } = useBatchStore();

  useEffect(() => {
    getBatches().then((result) => {
      if (result.data && Array.isArray(result.data)) {
        setBatches(result.data);
      }
      setLoading(false);
    });
  }, []);

  // Format date safely
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  // Calculate duration display
  const getDuration = (batch) => {
    if (batch.duration) return `${batch.duration} days`;
    if (batch.currentDay !== undefined) return `${batch.currentDay} / 16 days`;
    // If it's the active batch, use store currentDay
    if (activeBatch && batch.id === activeBatch.id) return `${currentDay} / 16 days`;
    return '-';
  };

  // Get biomass display
  const getBiomass = (batch) => {
    if (batch.finalBiomass) return batch.finalBiomass;
    if (batch.status === 'completed') return '~148 mg';
    return 'In Progress';
  };

  // Get policy display name
  const getPolicyLabel = (batch) => {
    const p = batch.policy || 'ppo';
    if (p === 'ppo' || p.toLowerCase().includes('ppo')) return 'PPO';
    if (p === 'rule_based' || p.toLowerCase().includes('heuristic')) return 'Heuristic';
    return p.toUpperCase();
  };

  // Filter batches by search
  const filteredBatches = batches.filter((b) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (b.id && b.id.toLowerCase().includes(q)) ||
      (b.startDate && b.startDate.toLowerCase().includes(q)) ||
      (b.policy && b.policy.toLowerCase().includes(q))
    );
  });

  // Handle clicking "Continue" on an active batch
  const handleContinueBatch = (batch) => {
    setActiveBatch(batch);
    navigate('/dashboard/checkin');
  };

  return (
    <div className="p-8 max-w-6xl mx-auto pb-24">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-display font-bold text-accent mb-2">Batch History</h1>
          <p className="text-text-muted">Review performance across all historical runs.</p>
        </div>
        <div className="relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search batches..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface-1 border border-border rounded-lg py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-primary/50 w-64"
          />
        </div>
      </div>

      {loading && <p className="text-text-muted">Loading batches...</p>}

      {!loading && filteredBatches.length === 0 && (
        <GlassCard className="p-8 text-center">
          <p className="text-text-muted text-lg mb-4">No batches found.</p>
          <button
            onClick={() => navigate('/dashboard/new')}
            className="text-primary hover:underline font-medium"
          >
            Start your first batch →
          </button>
        </GlassCard>
      )}

      {filteredBatches.length > 0 && (
        <GlassCard className="overflow-hidden">
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-2/50 text-xs uppercase tracking-widest text-text-muted">
                  <th className="p-4 font-bold">Batch ID</th>
                  <th className="p-4 font-bold">Start Date</th>
                  <th className="p-4 font-bold">Duration</th>
                  <th className="p-4 font-bold">Final Biomass</th>
                  <th className="p-4 font-bold">Policy</th>
                  <th className="p-4 font-bold">Status</th>
                  <th className="p-4 font-bold w-12 flex justify-center"></th>
                </tr>
              </thead>
              <tbody>
                {filteredBatches.map((batch) => {
                  const isExpanded = expandedRow === batch.id;
                  const isActive = batch.status === 'active';
                  const rowCls = "border-b border-border transition-colors hover:bg-primary/5 cursor-pointer " + (isExpanded ? "bg-primary/5" : "");
                  const policyLabel = getPolicyLabel(batch);
                  const policyCls = "text-xs px-2 py-1 rounded " + (policyLabel === 'PPO' ? "bg-primary/10 text-primary" : "bg-surface-2 text-text-muted border border-border");
                  const chevronCls = "w-5 h-5 text-text-muted transition-transform " + (isExpanded ? "rotate-180 text-primary" : "");

                  return (
                    <React.Fragment key={batch.id}>
                      <tr
                        className={rowCls}
                        onClick={() => setExpandedRow(isExpanded ? null : batch.id)}
                      >
                        <td className="p-4 font-bold text-accent">#{batch.id?.slice(-4) || batch.id}</td>
                        <td className="p-4 text-text-muted">{formatDate(batch.startDate || batch.createdAt)}</td>
                        <td className="p-4">{getDuration(batch)}</td>
                        <td className="p-4 font-display font-bold text-primary">{getBiomass(batch)}</td>
                        <td className="p-4">
                          <span className={policyCls}>
                            {policyLabel}
                          </span>
                        </td>
                        <td className="p-4">
                          {isActive ? (
                            <Badge className="animate-pulse shadow-glow">Active</Badge>
                          ) : (
                            <Badge className="bg-surface-2 text-text-muted border-border">Completed</Badge>
                          )}
                        </td>
                        <td className="p-4">
                          <ChevronDown className={chevronCls} />
                        </td>
                      </tr>

                      {/* Expanded Row Detail */}
                      <AnimatePresence>
                        {isExpanded && (
                          <tr>
                            <td colSpan={7} className="p-0 border-b border-border">
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.3 }}
                                className="bg-surface-2/30 overflow-hidden"
                              >
                                <div className="p-6 grid grid-cols-3 gap-6">
                                  <div className="col-span-2">
                                    <h4 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">Check-in Log</h4>
                                    <div className="space-y-3">
                                      {(batch.checkIns && batch.checkIns.length > 0) ? (
                                        batch.checkIns.slice().reverse().map((ci, idx) => (
                                          <div key={idx} className="flex gap-4 text-sm border-l-2 border-primary pl-3 bg-surface-1 py-2 px-3 rounded-r">
                                            <span className="font-mono text-text-muted shrink-0 w-14">Day {ci.day}</span>
                                            <span className="text-accent">{ci.recommendation || 'Check-in completed'}</span>
                                            <span className="text-text-muted ml-auto text-xs">{ci.feed_kg ? `${ci.feed_kg}kg` : ''}</span>
                                          </div>
                                        ))
                                      ) : (
                                        <>
                                          <div className="flex gap-4 text-sm border-l-2 border-border pl-3">
                                            <span className="font-mono text-text-muted shrink-0 w-14">Day 0</span>
                                            <span className="text-text-muted">Batch initialized.</span>
                                          </div>
                                        </>
                                      )}
                                    </div>

                                    {/* Continue button for active batches */}
                                    {isActive && (
                                      <button
                                        onClick={(e) => { e.stopPropagation(); handleContinueBatch(batch); }}
                                        className="mt-4 px-4 py-2 bg-primary/10 text-primary border border-primary/30 rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
                                      >
                                        Continue Check-in →
                                      </button>
                                    )}
                                  </div>
                                  <div>
                                    <h4 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">Batch Metrics</h4>
                                    <div className="space-y-4">
                                      <div>
                                        <div className="text-xs text-text-muted mb-1">Larvae Count</div>
                                        <div className="font-bold text-lg">{(batch.larvaeCount || 10000).toLocaleString()}</div>
                                      </div>
                                      <div>
                                        <div className="text-xs text-text-muted mb-1">Container</div>
                                        <div className="font-bold text-lg capitalize">{batch.containerSize || 'standard'}</div>
                                      </div>
                                      <div>
                                        <div className="text-xs text-text-muted mb-1">Total Feed Used</div>
                                        <div className="font-bold text-lg text-primary">
                                          {batch.checkIns
                                            ? batch.checkIns.reduce((sum, ci) => sum + (ci.feed_kg || ci.feedKg || 0), 0).toFixed(1) + ' kg'
                                            : '-'
                                          }
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </motion.div>
                            </td>
                          </tr>
                        )}
                      </AnimatePresence>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
