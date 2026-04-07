import axios from 'axios';
import { mockBatches, mockReport } from './mocks';

const client = axios.create({
  baseURL: '',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.resolve({ error: error.response || error.message });
  }
);

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const createBatch = async (data) => {
  try {
    const res = await client.post('/api/batches', data);
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(500);
    return { data: { id: Date.now().toString(), ...data, status: 'active' } };
  }
};

export const getBatches = async () => {
  try {
    const res = await client.get('/api/batches');
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(500);
    return { data: mockBatches };
  }
};

export const getBatch = async (id) => {
  try {
    const res = await client.get('/api/batches/' + id);
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(500);
    return { data: mockBatches.find((b) => b.id === id) || mockBatches[0] };
  }
};

export const submitCheckin = async (data) => {
  try {
    const res = await client.post('/api/checkin', data);
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(800);
    return {
      data: {
        schedule: [
          { time: '08:00 AM', mix: '2kg Veg + 1kg Bakery', h2o: '+500ml H2O' },
          { time: '02:00 PM', mix: '3kg Fruit', h2o: 'No added water' },
          { time: '06:00 PM', mix: '1kg Spent Grain', h2o: '+200ml H2O' },
        ],
        projection: { expected: '48mg', trajectory: 'Optimal' },
      },
    };
  }
};

export const saveCheckin = async (batchId, data) => {
  try {
    const res = await client.post(`/api/batches/${batchId}/checkin`, data);
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(300);
    return { data: { ok: true } };
  }
};

export const updateBatch = async (batchId, updates) => {
  try {
    const res = await client.patch(`/api/batches/${batchId}`, updates);
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(300);
    return { data: { ok: true } };
  }
};

export const getReport = async () => {
  try {
    const res = await client.get('/api/report');
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(600);
    return { data: mockReport };
  }
};

export const getSettings = async () => {
  try {
    const res = await client.get('/api/settings');
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(300);
    return { data: { policy: 'ppo' } };
  }
};

export const updatePolicy = async (policy) => {
  try {
    const res = await client.post('/api/settings/policy', { policy });
    if (res.error) throw res.error;
    return { data: res.data };
  } catch (err) {
    await delay(400);
    return { data: { policy } };
  }
};
