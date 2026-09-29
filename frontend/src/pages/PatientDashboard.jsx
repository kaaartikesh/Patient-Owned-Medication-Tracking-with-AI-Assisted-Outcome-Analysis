import { useAuth } from "../context/AuthContext";

function PatientDashboard() {
  const { user, logout } = useAuth();

  return (
    <div>
      <h1>Patient Dashboard</h1>
      <p>Welcome, {user.sub}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default PatientDashboard;