export const mockBatches = [
  { id: '204', date: '2023-11-20', duration: 8,  biomass: '-',     status: 'active',    policy: 'PPO Agent' },
  { id: '203', date: '2023-11-02', duration: 16, biomass: '148mg', status: 'completed', policy: 'PPO Agent' },
  { id: '202', date: '2023-10-15', duration: 16, biomass: '142mg', status: 'completed', policy: 'PPO Agent' },
  { id: '201', date: '2023-09-28', duration: 18, biomass: '134mg', status: 'completed', policy: 'Heuristic' },
  { id: '200', date: '2023-09-08', duration: 17, biomass: '131mg', status: 'completed', policy: 'Heuristic' },
];

export const mockReport = {
  strategies: [
    { name: 'PPO Agent',  avg_biomass: 122.34, std_biomass: 18.88, max_biomass: 145.14, avg_reward: 130.49, avg_feed_g: 970.18, avg_mortality: 73.66 },
    { name: 'Rule-Based', avg_biomass: 134.04, std_biomass: 18.65, max_biomass: 153.25, avg_reward: 135.42, avg_feed_g: 737.17, avg_mortality: 78.95 },
    { name: 'Random',     avg_biomass: 128.34, std_biomass: 21.38, max_biomass: 151.63, avg_reward: 126.33, avg_feed_g: 744.67, avg_mortality: 81.52 },
    { name: 'Do-Nothing', avg_biomass: 1.96,   std_biomass: 0.28,  max_biomass: 2.44,   avg_reward: -87.89, avg_feed_g: 0,      avg_mortality: 99.99 },
  ],
  highlights: {
    feed_savings_pct: -32,
    biomass_advantage_mg: -11.7,
    mortality_change_pct: 5.29,
  },
};
