import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GlassCard from '../../components/ui/GlassCard';
import Badge from '../../components/ui/Badge';
import { ChevronDown, Search } from 'lucide-react';
import { getBatches } from '../../api/client';
import { useBatchStore } from '../../store/batchStore';

export default function BatchHistory() {
  const [expandedRow, setExpandedRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const { batches, setBatches } = useBatchStore();

  useEffect(() => {
    getBatches().then((result) => {
      setBatches(result.data);
      setLoading(false);
    });
  }, []);

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
            className="bg-surface-1 border border-border rounded-lg py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-primary/50 w-64"
          />
        </div>
      </div>

      {loading && <p className="text-text-muted">Loading batches...</p>}

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
              {batches.map((batch) => {
                const isExpanded = expandedRow === batch.id;
                const rowCls = "border-b border-border transition-colors hover:bg-primary/5 cursor-pointer " + (isExpanded ? "bg-primary/5" : "");
                const policyCls = "text-xs px-2 py-1 rounded " + (batch.policy.includes('PPO') ? "bg-primary/10 text-primary" : "bg-surface-2 text-text-muted border border-border");
                const chevronCls = "w-5 h-5 text-text-muted transition-transform " + (isExpanded ? "rotate-180 text-primary" : "");

                return (
                  <React.Fragment key={batch.id}>
                    <tr 
                      className={rowCls}
                      onClick={() => setExpandedRow(isExpanded ? null : batch.id)}
                    >
                      <td className="p-4 font-bold text-accent">#{batch.id}</td>
                      <td className="p-4 text-text-muted">{batch.date}</td>
                      <td className="p-4">{batch.duration} days</td>
                      <td className="p-4 font-display font-bold text-primary">{batch.biomass}</td>
                      <td className="p-4">
                        <span className={policyCls}>
                          {batch.policy}
                        </span>
                      </td>
                      <td className="p-4">
                        {batch.status === 'active' ? (
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
                                  <h4 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">Log Highlights</h4>
                                  <div className="space-y-3">
                                    <div className="flex gap-4 text-sm border-l-2 border-primary pl-3 bg-surface-1 py-2 px-3 rounded-r">
                                      <span className="font-mono text-text-muted shrink-0 w-12">Day 8</span>
                                      <span className="text-accent">AI corrected C:N ratio to 18:1 based on rising moisture.</span>
                                    </div>
                                    <div className="flex gap-4 text-sm border-l-2 border-border pl-3">
                                      <span className="font-mono text-text-muted shrink-0 w-12">Day 5</span>
                                      <span className="text-text-muted">Transitioned to Exponential Growth phase.</span>
                                    </div>
                                    <div className="flex gap-4 text-sm border-l-2 border-border pl-3">
                                      <span className="font-mono text-text-muted shrink-0 w-12">Day 1</span>
                                      <span className="text-text-muted">Batch initialized.</span>
                                    </div>
                                  </div>
                                </div>
                                <div>
                                  <h4 className="text-sm font-bold text-text-muted uppercase tracking-widest mb-4">Batch Metrics</h4>
                                  <div className="space-y-4">
                                    <div>
                                      <div className="text-xs text-text-muted mb-1">Feed Efficiency</div>
                                      <div className="font-bold text-lg">1.52 <span className="text-sm text-text-muted font-normal">FCR</span></div>
                                    </div>
                                    <div>
                                      <div className="text-xs text-text-muted mb-1">Mortality Rate</div>
                                      <div className="font-bold text-lg text-primary">68%</div>
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
    </div>
  );
}
