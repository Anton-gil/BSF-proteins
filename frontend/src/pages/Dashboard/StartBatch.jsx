import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { ChevronDown } from 'lucide-react';
import { createBatch } from '../../api/client';
import { useBatchStore } from '../../store/batchStore';

export default function StartBatch() {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { batches, setBatches, setActiveBatch } = useBatchStore();

  const [formData, setFormData] = useState({
    larvaeCount: 10000,
    containerSize: 'standard',
    startDate: new Date().toISOString().split('T')[0],
    location: 'chennai'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    const result = await createBatch(formData);
    if (result.data) {
      setBatches([result.data, ...batches]);
      setActiveBatch(result.data);
    }
    navigate('/dashboard/checkin');
    setSubmitting(false);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto pb-24">
      <h1 className="text-3xl font-display font-bold text-accent mb-8">Start New Batch</h1>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Details */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-bold mb-6 text-accent">Batch Details</h2>
            
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Number of Larvae</label>
                <div className="flex gap-2">
                  <Button 
                    type="button" 
                    variant="ghost" 
                    onClick={() => setFormData(p => ({...p, larvaeCount: Math.max(0, p.larvaeCount - 1000)}))}
                  >-</Button>
                  <input 
                    type="number" 
                    value={formData.larvaeCount}
                    onChange={(e) => setFormData(p => ({...p, larvaeCount: parseInt(e.target.value) || 0}))}
                    className="flex-1 bg-surface-2 border border-border rounded-lg text-center font-display font-bold text-xl text-primary focus:outline-none focus:border-primary/50"
                  />
                  <Button 
                    type="button" 
                    variant="ghost"
                    onClick={() => setFormData(p => ({...p, larvaeCount: p.larvaeCount + 1000}))}
                  >+</Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Container Size</label>
                <select 
                  className="w-full bg-surface-2 border border-border rounded-lg py-3 px-4 text-text focus:outline-none focus:border-primary/50 appearance-none"
                  value={formData.containerSize}
                  onChange={(e) => setFormData(p => ({...p, containerSize: e.target.value}))}
                >
                  <option value="small">Small Tray (40x30 cm)</option>
                  <option value="standard">Standard Tray (60x40 cm)</option>
                  <option value="industrial">Industrial Bin (80x60 cm)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Start Date</label>
                <input 
                  type="date" 
                  value={formData.startDate}
                  onChange={(e) => setFormData(p => ({...p, startDate: e.target.value}))}
                  className="w-full bg-surface-2 border border-border rounded-lg py-3 px-4 text-text focus:outline-none focus:border-primary/50"
                />
              </div>
            </div>
          </GlassCard>

          {/* Right Column: Location */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-bold mb-6 text-accent">Farm Location</h2>
            
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Location Preset</label>
                <select 
                  className="w-full bg-surface-2 border border-border rounded-lg py-3 px-4 text-text focus:outline-none focus:border-primary/50 appearance-none"
                  value={formData.location}
                  onChange={(e) => setFormData(p => ({...p, location: e.target.value}))}
                >
                  <option value="chennai">Chennai HQ (Indoor Climate)</option>
                  <option value="bangalore">Bangalore Hub</option>
                  <option value="custom">Custom Location...</option>
                </select>
              </div>

              <div className="bg-surface-2 border border-border rounded-lg p-4 flex flex-col items-center justify-center h-40 relative overflow-hidden">
                <div className="absolute inset-0 opacity-20 pointer-events-none" 
                  style={{ backgroundImage: 'radial-gradient(circle at center, #84cc16 1px, transparent 1px)', backgroundSize: '10px 10px' }} 
                />
                <span className="text-primary tracking-widest font-mono text-sm relative z-10">13.0827° N, 80.2707° E</span>
                <span className="text-text-muted text-xs mt-2 relative z-10">Synced with Local Weather</span>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Expectation Accordion */}
        <div className="border border-border rounded-2xl bg-surface-1/40 overflow-hidden">
          <button 
            type="button" 
            className="w-full p-4 flex justify-between items-center text-text font-bold hover:bg-surface-2/50 transition-colors"
            onClick={() => setExpanded(!expanded)}
          >
            What to Expect
            <ChevronDown className={`w-5 h-5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
          
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="p-6 pt-0 border-t border-border mt-2 space-y-4">
                  <div className="flex gap-4 items-start">
                    <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 font-bold">1</div>
                    <div>
                      <h4 className="font-bold text-accent">Days 1-5: Establishment</h4>
                      <p className="text-text-muted text-sm mt-1">Minimal feeding required. The AI will primarily optimize for moisture levels and temperature stabilization in the tray.</p>
                    </div>
                  </div>
                  <div className="flex gap-4 items-start">
                    <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 font-bold">2</div>
                    <div>
                      <h4 className="font-bold text-accent">Days 6-12: Exponential Growth</h4>
                      <p className="text-text-muted text-sm mt-1">Daily check-ins become critical. You will be prompted for waste availability and given precise carbon-nitrogen target mix ratios.</p>
                    </div>
                  </div>
                  <div className="flex gap-4 items-start">
                    <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 font-bold">3</div>
                    <div>
                      <h4 className="font-bold text-accent">Days 13-16: Harvesting</h4>
                      <p className="text-text-muted text-sm mt-1">Feeding tapers off. AI will instruct you on drying the substrate prior to sieving.</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Button type="submit" size="lg" className="w-full h-14 text-lg" disabled={submitting}>
          {submitting ? 'Creating...' : 'Start Batch →'}
        </Button>
      </form>
    </div>
  );
}
