import { ShieldCheck, LogOut, User as UserIcon, Activity } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="nav-brand">
        <div className="brand-icon">
          <Activity size={22} />
        </div>
        <div>
          <div className="brand-title">AegisMed</div>
        </div>
        <span className="brand-badge">Patient Sovereign</span>
      </div>

      <div className="nav-user">
        {user && (
          <>
            <div className="user-badge">
              <UserIcon size={16} className="text-secondary" />
              <span>{user.name || user.email || user.sub}</span>
              <span className={`role-pill ${user.role}`}>
                {user.role}
              </span>
            </div>
            <button
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </>
        )}
      </div>
    </header>
  );
}
