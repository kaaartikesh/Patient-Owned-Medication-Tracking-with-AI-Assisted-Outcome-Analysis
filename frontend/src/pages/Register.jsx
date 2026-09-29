import { useState } from "react";
import { registerUser } from "../api/auth";

function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("patient");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await registerUser(email, password, role);
      console.log("Registered:", data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Register</h2>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="patient">Patient</option>
        <option value="doctor">Doctor</option>
      </select>
      <button type="submit">Register</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </form>
  );
}

export default Register;