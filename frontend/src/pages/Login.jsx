import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Activity, Lock, Mail, ArrowRight, AlertCircle, ShieldCheck } from "lucide-react";
import { loginUser } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [searchParams] = useSearchParams();
  const sessionMessage = searchParams.get("message");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(sessionMessage || "");
  const [loading, setLoading] = useState(false);
  const { user, login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.role) {
      navigate(`/${user.role}-dashboard`, { replace: true });
    }
  }, [user, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await loginUser(email, password);
      login(data.access_token);
      let role = "patient";
      try {
        const payload = JSON.parse(atob(data.access_token.split(".")[1]));
        if (payload?.role) role = payload.role;
      } catch {}
      navigate(`/${role}-dashboard`, { replace: true });
    } catch (err) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  function setDemoCredentials(demoEmail, demoPass) {
    setEmail(demoEmail);
    setPassword(demoPass);
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-icon" style={{ margin: "0 auto 1rem", width: 48, height: 48 }}>
            <Activity size={28} />
          </div>
          <h1>AegisMed</h1>
          <p className="auth-subtitle">
            Patient-Owned Medication Tracking & Outcome Intelligence
          </p>
        </div>

        {error && (
          <div className="alert-interaction" style={{ borderColor: "#ef4444", marginBottom: "1.25rem", animation: "none" }}>
            <AlertCircle size={20} color="#ef4444" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: "0.875rem", color: "#fca5a5" }}>{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div style={{ position: "relative" }}>
              <input
                type="email"
                className="form-input"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", marginTop: "0.5rem" }}
            disabled={loading}
          >
            {loading ? "Authenticating..." : "Sign In to Portal"}
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account? <Link to="/register">Create an account</Link>
        </div>
      </div>
    </div>
  );
}