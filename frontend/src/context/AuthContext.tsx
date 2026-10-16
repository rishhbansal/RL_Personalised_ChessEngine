import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import type { AuthUser, LoginRequest } from "../types/api";

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);


export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("demo_user");
    if (stored) setUser(JSON.parse(stored));
    setLoading(false);
  }, []);

  const login = async (data: LoginRequest) => {
    if (!data.email || !data.password) {
      throw new Error("Email and password are required");
    }

    const cleanEmail = data.email.trim().toLowerCase();
    const fakeUser: AuthUser = { id: `demo-${cleanEmail}`, email: cleanEmail };
    localStorage.setItem("demo_user", JSON.stringify(fakeUser));
    localStorage.setItem("last_demo_email", cleanEmail);
    setUser(fakeUser);
  };

  const logout = () => {
    localStorage.removeItem("demo_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}