import { useState, useEffect, useCallback } from 'react';
import { AuthContext } from './authContextDef';
import {
  getStoredToken,
  getStoredUser,
  loginUser as apiLogin,
  registerUser as apiRegister,
  fetchCurrentUser,
  logoutUser as apiLogout,
  clearAuthStorage,
} from '../services/authApi';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredToken());
  const [user, setUser] = useState(() => getStoredUser());
  const [loading, setLoading] = useState(true);

  // Initialize and verify authentication state on mount
  useEffect(() => {
    let isMounted = true;

    const verifyAuth = async () => {
      const storedToken = getStoredToken();
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setLoading(false);
        }
        return;
      }

      try {
        const verifiedUser = await fetchCurrentUser();
        if (!isMounted) return;
        if (verifiedUser) {
          setUser(verifiedUser);
          setToken(storedToken);
        } else {
          setUser(null);
          setToken(null);
          clearAuthStorage();
        }
      } catch {
        if (!isMounted) return;
        setUser(null);
        setToken(null);
        clearAuthStorage();
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    verifyAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const result = await apiLogin(email, password);
    setToken(result.access_token);
    setUser(result.user);
    return result;
  }, []);

  const register = useCallback(async (name, email, password) => {
    const result = await apiRegister(name, email, password);
    return result;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    role: user?.role || null,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
