import { create } from 'zustand';

export const useBatchStore = create((set) => ({
  activeBatch: null,
  batches: [],
  policy: 'ppo',
  todaySchedule: null,

  setActiveBatch: (batch) => set({ activeBatch: batch }),
  setBatches: (batches) => set({ batches }),
  setPolicy: (policy) => set({ policy }),
  setTodaySchedule: (schedule) => set({ todaySchedule: schedule }),
}));
