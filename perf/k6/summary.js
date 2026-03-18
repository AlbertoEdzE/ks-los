import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '10s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{name:v2_list_conversations}': ['p(95)<750'],
    'http_req_duration{name:v2_list_loans}': ['p(95)<750'],
    'http_req_duration{name:v2_send_message}': ['p(95)<2000'],
  },
};

export default function () {
  const baseUrl = __ENV.KS_LOS_BASE_URL || 'http://localhost:8000';
  const auth = __ENV.KS_LOS_AUTH || 'Bearer loan-officer-access';

  const headers = {
    Authorization: auth,
    'Content-Type': 'application/json',
    'X-Correlation-ID': 'k6-' + Math.random().toString(36).slice(2),
  };

  const createRes = http.post(
    `${baseUrl}/api/conversations`,
    JSON.stringify({ chatRole: 'officer' }),
    { headers, tags: { name: 'v2_create_conversation' } }
  );
  check(createRes, { 'create conversation 200': (r) => r.status === 200 });
  const conversationId = createRes.json('conversation.id');
  check(createRes, { 'has conversation id': () => typeof conversationId === 'string' && conversationId.length > 0 });

  const listConversationsRes = http.get(`${baseUrl}/api/conversations`, { headers, tags: { name: 'v2_list_conversations' } });
  check(listConversationsRes, { 'list conversations 200': (r) => r.status === 200 });

  const listLoansRes = http.get(`${baseUrl}/api/loans`, { headers, tags: { name: 'v2_list_loans' } });
  check(listLoansRes, { 'list loans 200': (r) => r.status === 200 });

  const sendRes = http.post(
    `${baseUrl}/api/conversations/${conversationId}/messages`,
    JSON.stringify({ content: 'set status to reviewing' }),
    { headers, tags: { name: 'v2_send_message' } }
  );
  check(sendRes, { 'send message 200': (r) => r.status === 200 });
  sleep(1);
}
