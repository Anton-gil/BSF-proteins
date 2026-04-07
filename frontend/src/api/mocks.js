export const mockBatches = [
  { id: '204', date: '2023-11-20', duration: 8, biomass: '-', status: 'active', policy: 'PPO Agent' },
  { id: '203', date: '2023-11-02', duration: 16, biomass: '148mg', status: 'completed', policy: 'PPO Agent' },
  { id: '202', date: '2023-10-15', duration: 16, biomass: '142mg', status: 'completed', policy: 'PPO Agent' },
];

export const mockReport = {
  metrics: {
    ppoAvg: 148,
    ruleAvg: 134,
    randomAvg: 128,
    doNothingAvg: 2
  },
  biomassData: Array.from({ length: 16 }, (_, i) => ({
    day: i + 1,
    ppo: Math.min(Math.pow(1.4, i) * 2, 148),
    rule: Math.min(Math.pow(1.35, i) * 2, 134),
  }))
};
