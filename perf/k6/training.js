import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 3,
  duration: '15s',
};

export default function () {
  const headers = { 'Content-Type': 'application/json', 'X-Correlation-ID': 'k6-' + Math.random().toString(36).slice(2) };
  const planRes = http.post('http://localhost:8000/training/plan', JSON.stringify({ rationale: 'Automated test' }), { headers });
  check(planRes, { 'plan 200': (r) => r.status === 200 });
  const plan = planRes.json('plan');
  const execRes = http.post('http://localhost:8000/training/execute', JSON.stringify(plan), { headers });
  check(execRes, { 'execute 200': (r) => r.status === 200 });
  const driftRes = http.post('http://localhost:8000/training/drift', null, { headers });
  check(driftRes, { 'drift 200': (r) => r.status === 200 });
  sleep(1);
}
