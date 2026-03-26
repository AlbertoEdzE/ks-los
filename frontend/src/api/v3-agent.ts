import axios from 'axios';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export interface V3ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface V3LoanSnapshot {
  loan_amount?: number;
  estimated_emi?: number;
  tenure_years?: number;
  interest_rate?: number;
  [key: string]: any;
}

export interface V3LoanRecommendation {
  name: string;
  type: string;
  monthly_emi: number;
  tenure_years: number;
  interest_rate: number;
  pros: string[];
  cons: string[];
  recommended: boolean;
}

export interface V3DocumentsChecklist {
  requiredNow?: Array<{name: string; description: string}>;
  [key: string]: any;
}

export interface V3ChatResponse {
  response: string;
  session_id: string;
  mode: 'advisory' | 'application' | 'completion';
  stage: string;
  confidence: number;
  metadata: {
    loan_snapshot?: V3LoanSnapshot;
    recommendations?: V3LoanRecommendation[];
    documents_checklist?: V3DocumentsChecklist;
    application_id?: string;
    stp_status?: string;
    escalation_needed?: boolean;
    [key: string]: any;
  };
}

export interface V3CreateConversationRequest {
  session_id?: string;
  borrower_name?: string;
}

export interface V3SendMessageRequest {
  content: string;
  session_id: string;
}

/**
 * Create a new v3 agentic conversation
 */
export const createConversation = async (
  request?: V3CreateConversationRequest
): Promise<V3ChatResponse> => {
  const response = await axios.post<V3ChatResponse>(
    `${API_URL}/api/v3/conversations/`,
    request || {}
  );
  return response.data;
};

/**
 * Send a message to the v3 agentic conversation
 * 
 * This uses the NEW LangGraph-based agentic workflow with:
 * - Advisory mode (understanding & estimation)
 * - Application mode (collection & submission)
 * - Completion mode (STP, acceptance, disbursement)
 * - Conversation repair mechanisms
 * - RAG policy-grounded responses
 * - Human escalation when needed
 */
export const sendMessage = async (
  message: string,
  session_id: string
): Promise<V3ChatResponse> => {
  const response = await axios.post<V3ChatResponse>(
    `${API_URL}/api/v3/conversations/messages`,
    {
      content: message,
      session_id
    }
  );
  return response.data;
};

/**
 * Get conversation state
 */
export const getConversation = async (
  session_id: string
): Promise<any> => {
  const response = await axios.get(
    `${API_URL}/api/v3/conversations/${session_id}`
  );
  return response.data;
};

/**
 * Delete conversation
 */
export const deleteConversation = async (
  session_id: string
): Promise<void> => {
  await axios.delete(`${API_URL}/api/v3/conversations/${session_id}`);
};
