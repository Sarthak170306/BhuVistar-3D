import { API_BASE_URL } from '../config/api';

const TOKEN_STORAGE_KEY = 'bhuvistaar_auth_token';
const USER_STORAGE_KEY = 'bhuvistaar_auth_user';

/**
 * Retrieves the persisted JWT token from localStorage.
 */
export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

/**
 * Persists the JWT token in localStorage.
 */
export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Graceful fallback for non-storage environments
  }
}

/**
 * Retrieves cached user metadata from localStorage.
 */
export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Persists user metadata in localStorage.
 */
export function setStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  } catch {
    // Graceful fallback
  }
}

/**
 * Completely clears stored authentication credentials.
 */
export function clearAuthStorage() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Graceful fallback
  }
}

/**
 * Returns Authorization header object if token exists.
 */
export function getAuthHeaders() {
  const token = getStoredToken();
  if (token) {
    return {
      Authorization: `Bearer ${token}`,
    };
  }
  return {};
}

/**
 * Authenticates user credentials via POST /api/v1/auth/login.
 */
export async function loginUser(email, password) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ email: email.trim(), password }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.error || 'Authentication failed. Please check credentials.';
    throw new Error(message);
  }

  if (data?.access_token && data?.user) {
    setStoredToken(data.access_token);
    setStoredUser(data.user);
  }

  return data;
}

/**
 * Public registration endpoint for Citizens via POST /api/v1/auth/register.
 */
export async function registerUser(name, email, password) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      name: name.trim(),
      email: email.trim(),
      password,
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.error || 'Registration failed. Please check your details.';
    throw new Error(message);
  }

  return data;
}

/**
 * Fetches current authenticated user profile via GET /api/v1/auth/me.
 */
export async function fetchCurrentUser() {
  const token = getStoredToken();
  if (!token) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearAuthStorage();
    }
    return null;
  }

  const user = await response.json().catch(() => null);
  if (user) {
    setStoredUser(user);
  }
  return user;
}

/**
 * Logs out user and discards client-side token.
 */
export async function logoutUser() {
  const token = getStoredToken();
  try {
    if (token) {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    }
  } catch {
    // Ignore network error during client-side logout
  } finally {
    clearAuthStorage();
  }
}
