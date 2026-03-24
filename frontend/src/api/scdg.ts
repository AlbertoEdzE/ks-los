import axios from 'axios';
import type { ApplicantCreditProfile } from '../types';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export const generateProfile = async (
  age: number,
  territory: string,
  scenario_type?: string,
  seed?: string
): Promise<ApplicantCreditProfile> => {
  const response = await axios.post<ApplicantCreditProfile>(`${API_URL}/scdg/generate`, {
    age,
    territory,
    scenario_type,
    seed,
  });
  return response.data;
};
