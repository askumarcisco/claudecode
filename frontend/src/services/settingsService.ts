import api from './api';

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

/**
 * Change the current user's password.
 *
 * TODO: backend endpoint not yet implemented — wire up when available.
 * The backend currently only exposes `PUT /auth/me` for updating `full_name`;
 * there is no `/auth/change-password` route yet. This call will 404 until
 * that endpoint ships. The UI surfaces an info Alert to set expectations
 * rather than pretending this works.
 */
export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await api.post('/auth/change-password', payload);
}
