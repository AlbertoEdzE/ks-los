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

export const sendMessage = async (
  message: string, 
  history: ChatMessage[] = []
): Promise<ChatResponse> => {
  const response = await axios.post<ChatResponse>(`${API_URL}/agent/chat`, {
    message,
    history,
    session_id: 'default' // Can be dynamic later
  });
  return response.data;
};
