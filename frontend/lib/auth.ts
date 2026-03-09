import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export type AppRole = 'manager' | 'coach';

export type AppUser = {
  user_id: string;
  email: string;
  role: AppRole;
};

export const AUTH_COOKIE_NAME = 'app_auth_token';

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL;

async function fetchCurrentUser(token: string): Promise<AppUser | null> {
  if (!AUTH_SERVICE_URL) {
    console.error('AUTH_SERVICE_URL is not defined');
    return null;
  }

  try {
    const response = await fetch(new URL('/api/auth/me', AUTH_SERVICE_URL).toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AppUser;
  } catch (error) {
    console.error('Failed to fetch current user', error);
    return null;
  }
}

export async function getCurrentUser(): Promise<AppUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  return fetchCurrentUser(token);
}

export async function requireCurrentUser(): Promise<AppUser> {
  const user = await getCurrentUser();
  if (!user) {
    redirect('/login');
  }
  return user;
}

export async function getAuthToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

export function getRoleAccessHeaders(user: AppUser): HeadersInit {
  return {
    'X-User-Id': user.user_id,
    'X-User-Role': user.role,
  };
}
