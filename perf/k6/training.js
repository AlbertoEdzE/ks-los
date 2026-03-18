import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 3,
  duration: '15s',
};

export default function () {
  const baseUrl = __ENV.KS_LOS_BASE_URL || 'http://localhost:8000';
  const auth = __ENV.KS_LOS_AUTH || 'Bearer loan-officer-access';
  const headers = {
    'Content-Type': 'application/json',
    'X-Correlation-ID': 'k6-' + Math.random().toString(36).slice(2),
    Authorization: auth,
  };
  const planRes = http.post(`${baseUrl}/training/plan`, JSON.stringify({ rationale: 'Automated test' }), { headers });
  const okPlan = check(planRes, { 'plan 200': (r) => r.status === 200 });
  if (!okPlan || !planRes.body) {
    sleep(1);
    return;
  }
  const plan = planRes.json('plan');
  const execRes = http.post(`${baseUrl}/training/execute`, JSON.stringify(plan), { headers });
  const okExec = check(execRes, { 'execute 200': (r) => r.status === 200 });
  if (!okExec) {
    sleep(1);
    return;
  }
  const driftRes = http.post(`${baseUrl}/training/drift`, null, { headers });
  check(driftRes, { 'drift 200': (r) => r.status === 200 });
  sleep(1);
}
