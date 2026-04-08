import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const LIFECYCLE_STAGES = [
  { start: 0, end: 2,  name: 'Neonate',           emoji: '🥚', focus: 'Moisture Control' },
  { start: 3, end: 5,  name: 'Early Growth',      emoji: '🐛', focus: 'Light Feeding' },
  { start: 6, end: 8,  name: 'Exponential Phase',  emoji: '🐛', focus: 'C:N Targeting' },
  { start: 9, end: 11, name: 'Late Growth',        emoji: '🐛', focus: 'Heavy Feeding' },
  { start: 12, end: 14, name: 'Pre-Pupa',          emoji: '🦋', focus: 'Tapering Feed' },
  { start: 15, end: 16, name: 'Harvest Ready',     emoji: '✅', focus: 'Harvest' },
];

export const getStageInfo = (day) => {
  for (const stage of LIFECYCLE_STAGES) {
    if (day >= stage.start && day <= stage.end) return stage;
  }
  return LIFECYCLE_STAGES[LIFECYCLE_STAGES.length - 1];
};

export const useBatchStore = create(
  persist(
    (set, get) => ({
      activeBatch: null,
      batches: [],
      policy: 'ppo',
      todaySchedule: null,
      currentDay: 0,
      checkIns: [],            // [{day, feedKg, recommendation, schedule, confirmedAt}]

      setActiveBatch: (batch) => set({
        activeBatch: batch,
        currentDay: 0,
        checkIns: [],
        todaySchedule: null,
      }),

      // Resume an existing batch preserving its currentDay and checkIns
      resumeBatch: (batch) => set({
        activeBatch: batch,
        currentDay: batch.currentDay ?? 0,
        checkIns: batch.checkIns ?? [],
        todaySchedule: null,
      }),

      setBatches: (batches) => set({ batches }),
      setPolicy: (policy) => set({ policy }),
      setTodaySchedule: (schedule) => set({ todaySchedule: schedule }),

      completeDay: (checkinRecord) => {
        const state = get();
        const newDay = state.currentDay + 1;
        const newCheckIns = [...state.checkIns, checkinRecord];

        // Update the batch in the batches list too
        const updatedBatches = state.batches.map((b) =>
          b.id === state.activeBatch?.id
            ? { ...b, currentDay: newDay, checkIns: newCheckIns }
            : b
        );

        set({
          currentDay: newDay,
          checkIns: newCheckIns,
          todaySchedule: null,
          batches: updatedBatches,
        });
      },

      clearHistory: () => {
        const state = get();
        // Keep only the active batch (if it has check-ins) in the list
        const kept = state.activeBatch && state.checkIns.length > 0
          ? [{ ...state.activeBatch, checkIns: state.checkIns }]
          : [];
        set({ batches: kept });
      },

      endBatch: () => {
        const state = get();
        const updatedBatches = state.batches.map((b) =>
          b.id === state.activeBatch?.id
            ? { ...b, status: 'completed', duration: state.currentDay }
            : b
        );
        set({
          activeBatch: null,
          currentDay: 0,
          checkIns: [],
          todaySchedule: null,
          batches: updatedBatches,
        });
      },
    }),
    { name: 'bsf-batch-store' }
  )
);
