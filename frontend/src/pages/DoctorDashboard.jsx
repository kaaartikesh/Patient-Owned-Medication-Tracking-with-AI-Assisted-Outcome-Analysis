import { useAuth } from "../context/AuthContext";

function DoctorDashboard() {
  const { user, logout } = useAuth();

  return (
    <div>
      <h1>Doctor Dashboard</h1>
      <p>Welcome, {user.sub}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default DoctorDashboard;