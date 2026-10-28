import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, UserPlus, AlertCircle, CheckCircle2 } from "lucide-react";
import { registerUser } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("patient");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();
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
      await registerUser(email, password, role, fullName);
      setSuccess(true);
      setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-icon" style={{ margin: "0 auto 1rem", width: 48, height: 48 }}>
            <Activity size={28} />
          </div>
          <h1>Join AegisMed</h1>
          <p className="auth-subtitle">
            Create an account to manage sovereign healthcare records
          </p>
        </div>

        {error && (
          <div className="alert-interaction" style={{ borderColor: "#ef4444", marginBottom: "1.25rem", animation: "none" }}>
            <AlertCircle size={20} color="#ef4444" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: "0.875rem", color: "#fca5a5" }}>{error}</div>
          </div>
        )}

        {success && (
          <div className="alert-interaction" style={{ background: "rgba(16, 185, 129, 0.15)", borderColor: "#10b981", marginBottom: "1.25rem", animation: "none" }}>
            <CheckCircle2 size={20} color="#10b981" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: "0.875rem", color: "#6ee7b7" }}>
              Account created successfully! Redirecting to login...
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Alice Smith or Dr. Bob Carter"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Account Role</label>
            <select
              className="form-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="patient">Patient (Sovereign Record Owner)</option>
              <option value="doctor">Doctor (Licensed Clinician)</option>
            </select>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", marginTop: "0.5rem" }}
            disabled={loading || success}
          >
            {loading ? "Creating Account..." : "Complete Registration"}
            <UserPlus size={18} />
          </button>
        </form>

        <div className="auth-footer">
          Already registered? <Link to="/login">Sign in here</Link>
        </div>
      </div>
    </div>
  );
}