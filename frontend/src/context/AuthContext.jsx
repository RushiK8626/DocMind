import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, getMe } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(true);

  // On mount (or token change), try to fetch the current user
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    getMe()
      .then((data) => setUser(data))
      .catch(() => {
        // Token invalid / expired
        localStorage.removeItem('access_token');
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    localStorage.setItem('access_token', data.access_token);
    setToken(data.access_token);
    // getMe will fire via the useEffect above
  }, []);

  const registerUser = useCallback(async (email, username, password) => {
    await apiRegister(email, username, password);
    // After registration, auto-login
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
  }, []);

  const value = { user, token, loading, login, register: registerUser, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
