import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "../lib/api";

interface User {
  id: string;
  email: string;
  full_name?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize session from localStorage
    const savedToken = localStorage.getItem("niftymind_token");
    const savedUser = localStorage.getItem("niftymind_user");
    
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const data = await api.post("/auth/login", { email, password });
      
      const userPayload: User = {
        id: data.user.id,
        email: data.user.email,
        full_name: data.user.full_name,
      };

      setToken(data.access_token);
      setUser(userPayload);
      
      localStorage.setItem("niftymind_token", data.access_token);
      localStorage.setItem("niftymind_user", JSON.stringify(userPayload));
    } catch (err) {
      throw err;
    }
  };

  const register = async (email: string, password: string, fullName: string) => {
    try {
      const data = await api.post("/auth/register", {
        email,
        password,
        full_name: fullName,
      });

      const userPayload: User = {
        id: data.user.id,
        email: data.user.email,
        full_name: data.user.full_name,
      };

      setToken(data.access_token);
      setUser(userPayload);

      localStorage.setItem("niftymind_token", data.access_token);
      localStorage.setItem("niftymind_user", JSON.stringify(userPayload));
    } catch (err) {
      throw err;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("niftymind_token");
    localStorage.removeItem("niftymind_user");
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
