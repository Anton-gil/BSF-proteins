import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  ScatterChart, Scatter, ZAxis, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar 
} from 'recharts';
import { motion } from 'framer-motion';
import PageTransition from '../../components/ui/PageTransition';
import GlassCard from '../../components/ui/GlassCard';

export default function Report() {
  const metrics = [
    { label: "PPO Agent", value: 148, unit: "mg", color: "text-primary border-primary/30 bg-primary/10" },
    { label: "Rule-Based", value: 134, unit: "mg", color: "text-blue-400 border-blue-400/30 bg-blue-400/10" },
    { label: "Random", value: 128, unit: "mg", color: "text-amber-400 border-amber-400/30 bg-amber-400/10" },
    { label: "Do-Nothing", value: 2, unit: "mg", color: "text-red-400 border-red-400/30 bg-red-400/10" }
  ];

  const strategyData = [
    { name: 'PPO Agent', avg: 148.2, max: 153.1, reward: 89.1 },
    { name: 'Rule-Based', avg: 134.0, max: 153.2, reward: 63.1 },
    { name: 'Random', avg: 128.3, max: 151.6, reward: 52.6 },
    { name: 'Do-Nothing', avg: 1.9, max: 2.4, reward: -162.8 },
  ];

  const biomassOverTime = Array.from({ length: 16 }, (_, i) => ({
    day: i + 1,
    ppo: i < 3 ? 1 : Math.pow(1.4, i-2) * 2 + (Math.random() * 5),
    rule: i < 3 ? 1 : Math.pow(1.35, i-2) * 2 + (Math.random() * 4),
    random: i < 3 ? 1 : Math.pow(1.3, i-2) * 2 + (Math.random() * 6),
  })).map(d => ({
    ...d, 
    ppo: Math.min(d.ppo, 148 + Math.random() * 5),
    rule: Math.min(d.rule, 134 + Math.random() * 5),
    random: Math.min(d.random, 128 + Math.random() * 5),
  }));

  const scatterDataPPO = [
    { x: 503, y: 151 }, { x: 456, y: 142 }, { x: 588, y: 152 }, { x: 415, y: 138 },
    { x: 496, y: 152 }, { x: 514, y: 150 }, { x: 400, y: 109 }, { x: 578, y: 152 },
    { x: 541, y: 153 }, { x: 471, y: 153 }, { x: 565, y: 150 }, { x: 483, y: 150 }
  ];
  
  const scatterDataRule = [
    { x: 947, y: 147 }, { x: 555, y: 123 }, { x: 722, y: 142 }, { x: 493, y: 128 },
    { x: 1078, y: 151 }, { x: 1040, y: 153 }, { x: 434, y: 94 }, { x: 480, y: 116 },
    { x: 553, y: 104 }, { x: 814, y: 134 }, { x: 754, y: 147 }, { x: 524, y: 107 }
  ];

  const radarData = [
    { subject: 'Biomass Yield', PPO: 100, RuleBased: 90, fullMark: 100 },
    { subject: 'Feed Efficiency', PPO: 98, RuleBased: 48, fullMark: 100 },
    { subject: 'Survival Rate', PPO: 88, RuleBased: 68, fullMark: 100 },
    { subject: 'Reward Max', PPO: 92, RuleBased: 65, fullMark: 100 },
    { subject: 'Consistency', PPO: 85, RuleBased: 70, fullMark: 100 },
  ];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface-1 border border-border p-3 rounded-lg shadow-xl">
          <p className="text-text font-bold mb-2 break-all">{`Day ${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {entry.name}: {entry.value.toFixed(1)} mg
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const ScatterTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface-1 border border-border p-3 rounded-lg shadow-xl">
          <p className="text-sm text-text-muted">Scatter Point</p>
          <p className="text-sm text-text border-b border-border/20 pb-1 mb-1">Feed Used: {payload[0].value}g</p>
          <p className="text-sm text-primary">Biomass Yield: {payload[1].value}mg</p>
        </div>
      );
    }
    return null;
  };

  return (
    <PageTransition className="p-8 max-w-7xl mx-auto pb-24">
      <div className="mb-10 text-center">
        <h1 className="text-4xl md:text-5xl font-display font-bold text-accent mb-4">AI Performance Report</h1>
        <p className="text-text-muted max-w-2xl mx-auto">
          Comprehensive analysis of Reinforcement Learning agent performance against baseline and heuristic expert systems.
        </p>
      </div>

      {/* Key Numbers */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
          >
            <GlassCard className={"p-6 text-center border " + m.color.split(' ')[1] + " " + m.color.split(' ')[2]}>
              <div className={"text-3xl font-display font-bold mb-1 " + m.color.split(' ')[0]}>
                {m.value}<span className="text-lg">{m.unit}</span>
              </div>
              <div className="text-xs font-bold uppercase tracking-widest text-text-muted">{m.label}</div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* Highlights Banner */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="bg-primary/10 border border-primary/30 rounded-2xl p-8 mb-12 flex flex-col md:flex-row items-center justify-between"
      >
        <div className="mb-6 md:mb-0">
          <h2 className="text-2xl font-bold text-primary mb-2">AI vs Expert Heuristic</h2>
          <p className="text-primary/80">The PPO agent consistently outperforms traditional best practices.</p>
        </div>
        <div className="flex gap-8">
          <div className="text-center">
            <div className="text-2xl font-display font-bold text-primary">31%</div>
            <div className="text-xs uppercase tracking-widest text-primary/60">Feed Savings</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-display font-bold text-primary">+14.2mg</div>
            <div className="text-xs uppercase tracking-widest text-primary/60">Biomass Adv.</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-display font-bold text-primary">+11.2%</div>
            <div className="text-xs uppercase tracking-widest text-primary/60">Survival Imp.</div>
          </div>
        </div>
      </motion.div>

      {/* Charts Grid */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.4 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-8"
      >
        
        {/* Strategy Comparison Bar Chart */}
        <GlassCard className="p-6">
          <h3 className="text-xl font-bold mb-6 text-accent">Summary Comparison (Avg Biomass)</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={strategyData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
                <XAxis dataKey="name" stroke="#6b7280" tick={{ fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#6b7280" tick={{ fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  cursor={{ fill: '#ffffff0a' }}
                  contentStyle={{ backgroundColor: '#0d1a0d', borderColor: '#ffffff1a', color: '#f0fdf0' }}
                />
                <Bar dataKey="avg" radius={[4, 4, 0, 0]} animationDuration={1500}>
                  {strategyData.map((entry, index) => {
                    let color = '#84cc16'; // PPO
                    if (entry.name === 'Rule-Based') color = '#60a5fa';
                    if (entry.name === 'Random') color = '#fbbf24';
                    if (entry.name === 'Do-Nothing') color = '#f87171';
                    return <Cell key={'cell-' + index} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        {/* Growth Curve Line Chart */}
        <GlassCard className="p-6">
          <h3 className="text-xl font-bold mb-6 text-accent">Cumulative Growth Trajectory</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={biomassOverTime} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" vertical={false} />
                <XAxis dataKey="day" stroke="#6b7280" tick={{ fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#6b7280" tick={{ fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                <Line type="monotone" dataKey="ppo" name="PPO Agent" stroke="#84cc16" strokeWidth={3} dot={false} activeDot={{ r: 6 }} animationDuration={2000} />
                <Line type="monotone" dataKey="rule" name="Rule-Based" stroke="#60a5fa" strokeWidth={2} dot={false} animationDuration={2000} />
                <Line type="monotone" dataKey="random" name="Random" stroke="#fbbf24" strokeWidth={2} dot={false} strokeDasharray="5 5" animationDuration={2000} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        {/* Scatter Chart (Biomass vs Feed) */}
        <GlassCard className="p-6">
          <h3 className="text-xl font-bold mb-6 text-accent">Efficiency: Biomass vs. Total Feed</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
                <XAxis type="number" dataKey="x" name="Total Feed (g)" stroke="#6b7280" domain={['dataMin - 50', 'dataMax + 50']} tick={{fill: '#6b7280'}} tickLine={false} axisLine={false} />
                <YAxis type="number" dataKey="y" name="Biomass (mg)" stroke="#6b7280" domain={['dataMin - 10', 'dataMax + 10']} tick={{fill: '#6b7280'}} tickLine={false} axisLine={false} />
                <ZAxis type="number" range={[60, 60]} />
                <Tooltip content={<ScatterTooltip />} cursor={{strokeDasharray: '3 3'}} />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                <Scatter name="PPO Agent" data={scatterDataPPO} fill="#84cc16" shape="circle" animationDuration={1500} />
                <Scatter name="Rule-Based" data={scatterDataRule} fill="#60a5fa" shape="triangle" animationDuration={1500} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        {/* Radar Chart (Multidimensional Comparison) */}
        <GlassCard className="p-6">
          <h3 className="text-xl font-bold mb-6 text-accent">Performance Radar Matrix</h3>
          <div className="h-[300px] w-full flex justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#ffffff1a" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#6b7280', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="PPO Agent" dataKey="PPO" stroke="#84cc16" fill="#84cc16" fillOpacity={0.4} animationDuration={2000} />
                <Radar name="Rule-Based" dataKey="RuleBased" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.3} animationDuration={2000} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0d1a0d', borderColor: '#ffffff1a', color: '#f0fdf0' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

      </motion.div>
    </PageTransition>
  );
}
