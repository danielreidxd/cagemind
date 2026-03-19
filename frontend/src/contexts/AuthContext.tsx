import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';

interface User {
  username: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAdmin: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAdmin: false,
  login: async () => {},
  logout: () => {},
  loading: true,
});

const API_BASE = import.meta.env.PROD
  ? 'https://web-production-2bc52.up.railway.app'
  : '/api';

const TOKEN_KEY = 'cagemind_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore token from sessionStorage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem(TOKEN_KEY);
    if (saved) {
      // Verify token is still valid
      fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${saved}` },
      })
        .then((r) => {
          if (r.ok) return r.json();
          throw new Error('Token expired');
        })
        .then((data) => {
          setUser({ username: data.username, role: data.role });
          setToken(saved);
        })
        .catch(() => {
          sessionStorage.removeItem(TOKEN_KEY);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error de conexión' }));
      throw new Error(err.detail || 'Error al iniciar sesión');
    }

    const data = await res.json();
    setToken(data.token);
    setUser({ username: data.username, role: data.role });
    sessionStorage.setItem(TOKEN_KEY, data.token);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem(TOKEN_KEY);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAdmin: user?.role === 'admin',
        login,
        logout,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
