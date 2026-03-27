import axios from 'axios';
import type { ApplicantCreditProfile } from '../types';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  response: string;
  credit_profile?: ApplicantCreditProfile;
  risk_score?: number;
  advice?: string;
}

/**
 * Send a message to the NEW v3 agentic conversation flow.
 * 
 * This uses the LangGraph-based agentic workflow with:
 * - Advisory mode (understanding & estimation)
 * - Application mode (collection & submission)
 * - Completion mode (STP, acceptance, disbursement)
 * - Conversation repair mechanisms
 * - RAG policy-grounded responses
 * - Human escalation when needed
 */
export const sendMessage = async (
  message: string,
  _history: ChatMessage[] = []
): Promise<ChatResponse> => {
  void _history;
  // Use v3 agentic endpoint
  const response = await axios.post<ChatResponse>(`${API_URL}/api/v3/conversations/messages`, {
    content: message,
    session_id: 'default' // Can be dynamic later
  });
  
  // Map v3 response to legacy ChatResponse format
  return {
    response: response.data.response,
    // Map other fields as needed
  };
};
