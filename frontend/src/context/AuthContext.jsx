import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

function decodeToken(token) {
  const payload = token.split(".")[1];
  return JSON.parse(atob(payload));
}

export function AuthProvider({ children }) {
  const storedToken = localStorage.getItem("token");
  const initialUser = storedToken ? decodeToken(storedToken) : null;

  const [token, setToken] = useState(storedToken);
  const [user, setUser] = useState(initialUser);

  function login(newToken) {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    setUser(decodeToken(newToken));
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
// What this does: decodeToken pulls apart a JWT (which has three dot-separated parts) and reads the middle part — that's where your backend put sub (user id) and role when it created the token. AuthProvider checks localStorage once when the app starts (so refreshing the page doesn't log you out), and exposes login()/logout() functions plus the current user info to every part of the app that needs it.