import { createContext, useContext, useState, useEffect } from "react";
import { getMe } from "../api/index";

const AuthContext = createContext(null);

function decodeToken(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const storedToken = localStorage.getItem("token");
  const initialUser = storedToken ? decodeToken(storedToken) : null;

  const [token, setToken] = useState(storedToken);
  const [user, setUser] = useState(initialUser);

  useEffect(() => {
    if (token) {
      getMe()
        .then((profile) => {
          setUser((prev) => ({ ...prev, ...profile }));
        })
        .catch(() => {
          logout();
        });
    }
  }, [token]);

  function login(newToken) {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    const decoded = decodeToken(newToken);
    setUser(decoded);
    getMe()
      .then((profile) => {
        setUser((prev) => ({ ...prev, ...profile }));
      })
      .catch(() => {});
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout, refreshUser: () => getMe().then(setUser) }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}