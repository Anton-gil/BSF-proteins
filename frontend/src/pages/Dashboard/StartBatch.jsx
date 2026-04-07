import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { ChevronDown, Search } from 'lucide-react';
import { createBatch } from '../../api/client';
import { useBatchStore } from '../../store/batchStore';

// Indian cities with real coordinates for Open-Meteo weather API
const LOCATIONS = [
  // Tamil Nadu
  { id: 'chennai',       label: 'Chennai',         state: 'Tamil Nadu',     lat: 13.0827, lng: 80.2707 },
  { id: 'coimbatore',    label: 'Coimbatore',       state: 'Tamil Nadu',     lat: 11.0168, lng: 76.9558 },
  { id: 'madurai',       label: 'Madurai',          state: 'Tamil Nadu',     lat: 9.9252,  lng: 78.1198 },
  { id: 'salem',         label: 'Salem',            state: 'Tamil Nadu',     lat: 11.6643, lng: 78.1460 },
  { id: 'trichy',        label: 'Tiruchirappalli',  state: 'Tamil Nadu',     lat: 10.7905, lng: 78.7047 },
  { id: 'tirunelveli',   label: 'Tirunelveli',      state: 'Tamil Nadu',     lat: 8.7139,  lng: 77.7567 },
  { id: 'vellore',       label: 'Vellore',          state: 'Tamil Nadu',     lat: 12.9165, lng: 79.1325 },
  // Karnataka
  { id: 'bangalore',     label: 'Bengaluru',        state: 'Karnataka',      lat: 12.9716, lng: 77.5946 },
  { id: 'mysore',        label: 'Mysuru',           state: 'Karnataka',      lat: 12.2958, lng: 76.6394 },
  { id: 'hubli',         label: 'Hubballi',         state: 'Karnataka',      lat: 15.3647, lng: 75.1240 },
  { id: 'mangalore',     label: 'Mangaluru',        state: 'Karnataka',      lat: 12.9141, lng: 74.8560 },
  // Kerala
  { id: 'kochi',         label: 'Kochi',            state: 'Kerala',         lat: 9.9312,  lng: 76.2673 },
  { id: 'thiruvananthapuram', label: 'Thiruvananthapuram', state: 'Kerala', lat: 8.5241,  lng: 76.9366 },
  { id: 'kozhikode',     label: 'Kozhikode',        state: 'Kerala',         lat: 11.2588, lng: 75.7804 },
  { id: 'thrissur',      label: 'Thrissur',         state: 'Kerala',         lat: 10.5276, lng: 76.2144 },
  // Andhra Pradesh / Telangana
  { id: 'hyderabad',     label: 'Hyderabad',        state: 'Telangana',      lat: 17.3850, lng: 78.4867 },
  { id: 'visakhapatnam', label: 'Visakhapatnam',    state: 'Andhra Pradesh', lat: 17.6868, lng: 83.2185 },
  { id: 'vijayawada',    label: 'Vijayawada',       state: 'Andhra Pradesh', lat: 16.5062, lng: 80.6480 },
  { id: 'warangal',      label: 'Warangal',         state: 'Telangana',      lat: 17.9689, lng: 79.5941 },
  // Maharashtra
  { id: 'mumbai',        label: 'Mumbai',           state: 'Maharashtra',    lat: 19.0760, lng: 72.8777 },
  { id: 'pune',          label: 'Pune',             state: 'Maharashtra',    lat: 18.5204, lng: 73.8567 },
  { id: 'nagpur',        label: 'Nagpur',           state: 'Maharashtra',    lat: 21.1458, lng: 79.0882 },
  { id: 'aurangabad',    label: 'Aurangabad',       state: 'Maharashtra',    lat: 19.8762, lng: 75.3433 },
  // Gujarat
  { id: 'ahmedabad',     label: 'Ahmedabad',        state: 'Gujarat',        lat: 23.0225, lng: 72.5714 },
  { id: 'surat',         label: 'Surat',            state: 'Gujarat',        lat: 21.1702, lng: 72.8311 },
  { id: 'vadodara',      label: 'Vadodara',         state: 'Gujarat',        lat: 22.3072, lng: 73.1812 },
  // Rajasthan
  { id: 'jaipur',        label: 'Jaipur',           state: 'Rajasthan',      lat: 26.9124, lng: 75.7873 },
  { id: 'jodhpur',       label: 'Jodhpur',          state: 'Rajasthan',      lat: 26.2389, lng: 73.0243 },
  // North India
  { id: 'delhi',         label: 'New Delhi',        state: 'Delhi',          lat: 28.6139, lng: 77.2090 },
  { id: 'lucknow',       label: 'Lucknow',          state: 'Uttar Pradesh',  lat: 26.8467, lng: 80.9462 },
  { id: 'kanpur',        label: 'Kanpur',           state: 'Uttar Pradesh',  lat: 26.4499, lng: 80.3319 },
  { id: 'patna',         label: 'Patna',            state: 'Bihar',          lat: 25.5941, lng: 85.1376 },
  { id: 'bhopal',        label: 'Bhopal',           state: 'Madhya Pradesh', lat: 23.2599, lng: 77.4126 },
  { id: 'indore',        label: 'Indore',           state: 'Madhya Pradesh', lat: 22.7196, lng: 75.8577 },
  // East India
  { id: 'kolkata',       label: 'Kolkata',          state: 'West Bengal',    lat: 22.5726, lng: 88.3639 },
  { id: 'bhubaneswar',   label: 'Bhubaneswar',      state: 'Odisha',         lat: 20.2961, lng: 85.8245 },
  { id: 'guwahati',      label: 'Guwahati',         state: 'Assam',          lat: 26.1445, lng: 91.7362 },
  // Punjab / Haryana
  { id: 'chandigarh',    label: 'Chandigarh',       state: 'Punjab/Haryana', lat: 30.7333, lng: 76.7794 },
  { id: 'amritsar',      label: 'Amritsar',         state: 'Punjab',         lat: 31.6340, lng: 74.8723 },
  // Others
  { id: 'goa',           label: 'Panaji (Goa)',     state: 'Goa',            lat: 15.4909, lng: 73.8278 },
];

export default function StartBatch() {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [locationSearch, setLocationSearch] = useState('');
  const [showLocationList, setShowLocationList] = useState(false);
  const { batches, setBatches, setActiveBatch } = useBatchStore();

  const [formData, setFormData] = useState({
    larvaeCount: 10000,
    containerSize: 'standard',
    startDate: new Date().toISOString().split('T')[0],
    location: 'chennai',
    lat: 13.0827,
    lng: 80.2707,
  });

  // Selected location object
  const selectedLocation = LOCATIONS.find(l => l.id === formData.location) || LOCATIONS[0];

  // Filtered list for search
  const filteredLocations = useMemo(() => {
    const q = locationSearch.toLowerCase();
    if (!q) return LOCATIONS;
    return LOCATIONS.filter(l =>
      l.label.toLowerCase().includes(q) || l.state.toLowerCase().includes(q)
    );
  }, [locationSearch]);

  const handleSelectLocation = (loc) => {
    setFormData(p => ({ ...p, location: loc.id, lat: loc.lat, lng: loc.lng }));
    setLocationSearch('');
    setShowLocationList(false);
  };

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

            <div className="space-y-4">
              {/* Search input */}
              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Search City / State</label>
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Type city or state..."
                    value={locationSearch}
                    onChange={(e) => { setLocationSearch(e.target.value); setShowLocationList(true); }}
                    onFocus={() => setShowLocationList(true)}
                    className="w-full bg-surface-2 border border-border rounded-lg py-2.5 pl-9 pr-4 text-text text-sm focus:outline-none focus:border-primary/50"
                  />
                </div>
              </div>

              {/* City list */}
              <div className="max-h-44 overflow-y-auto rounded-lg border border-border bg-surface-2 divide-y divide-border">
                {filteredLocations.map((loc) => (
                  <button
                    key={loc.id}
                    type="button"
                    onClick={() => handleSelectLocation(loc)}
                    className={
                      "w-full text-left px-4 py-2.5 text-sm transition-colors flex justify-between items-center gap-2 " +
                      (formData.location === loc.id
                        ? "bg-primary/10 text-primary"
                        : "text-text hover:bg-surface-2/80")
                    }
                  >
                    <span className="font-medium">{loc.label}</span>
                    <span className="text-[11px] text-text-muted shrink-0">{loc.state}</span>
                  </button>
                ))}
                {filteredLocations.length === 0 && (
                  <div className="px-4 py-3 text-sm text-text-muted">No cities found.</div>
                )}
              </div>

              {/* Live coordinate display */}
              <div className="bg-surface-2 border border-border rounded-lg p-4 flex flex-col items-center justify-center relative overflow-hidden">
                <div
                  className="absolute inset-0 opacity-20 pointer-events-none"
                  style={{ backgroundImage: 'radial-gradient(circle at center, #84cc16 1px, transparent 1px)', backgroundSize: '10px 10px' }}
                />
                <span className="text-xs text-text-muted relative z-10 mb-1 font-bold uppercase tracking-widest">
                  {selectedLocation.label}, {selectedLocation.state}
                </span>
                <span className="text-primary tracking-widest font-mono text-sm relative z-10">
                  {selectedLocation.lat.toFixed(4)}° N, {selectedLocation.lng.toFixed(4)}° E
                </span>
                <span className="text-text-muted text-xs mt-2 relative z-10">📡 Live weather via Open-Meteo API</span>
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

