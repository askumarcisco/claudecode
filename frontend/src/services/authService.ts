import api from './api';
import type { User } from '../types';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string | null;
}

export interface UpdateMePayload {
  full_name?: string | null;
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/register', payload);
  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new FormData();
  form.append('username', email);
  form.append('password', password);
  const { data } = await api.post<TokenResponse>('/auth/login', form);
  return data;
}

export async function refresh(refreshToken: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout');
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export async function updateMe(payload: UpdateMePayload): Promise<User> {
  const { data } = await api.put<User>('/auth/me', payload);
  return data;
}
