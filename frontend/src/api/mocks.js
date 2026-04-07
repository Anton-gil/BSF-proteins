export const mockBatches = [
  { id: '204', date: '2023-11-20', duration: 8,  biomass: '-',     status: 'active',    policy: 'PPO Agent' },
  { id: '203', date: '2023-11-02', duration: 16, biomass: '148mg', status: 'completed', policy: 'PPO Agent' },
  { id: '202', date: '2023-10-15', duration: 16, biomass: '142mg', status: 'completed', policy: 'PPO Agent' },
  { id: '201', date: '2023-09-28', duration: 18, biomass: '134mg', status: 'completed', policy: 'Heuristic' },
  { id: '200', date: '2023-09-08', duration: 17, biomass: '131mg', status: 'completed', policy: 'Heuristic' },
];

export const mockReport = {
  strategies: [
    { name: 'PPO Agent',  avg_biomass: 148.2, max_biomass: 153.1, avg_reward: 89.1  },
    { name: 'Rule-Based', avg_biomass: 134.0, max_biomass: 153.2, avg_reward: 63.1  },
    { name: 'Random',     avg_biomass: 128.3, max_biomass: 151.6, avg_reward: 52.7  },
    { name: 'Do-Nothing', avg_biomass: 2.0,   max_biomass: 2.4,   avg_reward: -162.9 },
  ],
  highlights: {
    feed_savings_pct: 31,
    biomass_advantage_mg: 14.2,
    survival_improvement_pct: 11.2,
  },
};
