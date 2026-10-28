import { useState, useEffect, useRef } from "react";
import {
  Users,
  Clock,
  Pill,
  ShieldAlert,
  ShieldCheck,
  Plus,
  Send,
  AlertTriangle,
  HeartPulse,
  CheckCircle,
  XCircle,
  FileText,
  Activity,
  UserCheck,
  RefreshCw,
  Search,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import {
  getMyLinks,
  requestLink,
  getMedications,
  addMedication,
  getInteractions,
  getPatientEffectiveness,
  getPatientConsents,
  startEncounter,
  closeEncounter,
  getPatientEncounters,
} from "../api/index";

export default function DoctorDashboard() {
  const { user } = useAuth();
  const doctorId = user?.doctor_id;

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rosterError, setRosterError] = useState(null);

  // Doctor state
  const [links, setLinks] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  // Patient workspace data
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState(null);
  const [patientMeds, setPatientMeds] = useState([]);
  const [patientInteractions, setPatientInteractions] = useState([]);
  const [patientOutcomes, setPatientOutcomes] = useState([]);
  const [patientConsents, setPatientConsents] = useState([]);
  const [patientEncounters, setPatientEncounters] = useState([]);

  // Active Encounter tracking & countdown
  const [activeEncounter, setActiveEncounter] = useState(null);
  const [countdownSeconds, setCountdownSeconds] = useState(0);
  const [isEncounterExpired, setIsEncounterExpired] = useState(false);

  // Modals
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showPrescribeModal, setShowPrescribeModal] = useState(false);
  const [showStartEncounterModal, setShowStartEncounterModal] = useState(false);

  // Forms
  const [connectEmail, setConnectEmail] = useState("");
  const [requestEmail, setRequestEmail] = useState("");
  const [requestResult, setRequestResult] = useState(null);
  const [encounterDuration, setEncounterDuration] = useState(60);
  const [prescriptionData, setPrescriptionData] = useState({
    medication_name: "",
    dosage: "",
    frequency: "",
    notes: "",
  });

  const [actionLoading, setActionLoading] = useState({});
  const [statusMessage, setStatusMessage] = useState({ text: "", type: "" });
  const [interactionAlert, setInteractionAlert] = useState(null);

  function showNotification(text, type = "success") {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage({ text: "", type: "" }), 4000);
  }

  function formatCountdown(totalSec) {
    if (totalSec <= 0) return "00:00";
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  }

  async function loadDoctorData() {
    try {
      setRefreshing(true);
      setRosterError(null);
      const linksData = await getMyLinks();
      setLinks(linksData || []);

      if (linksData && linksData.length > 0 && !selectedPatient) {
        // Auto-select first active patient
        const firstActive = linksData.find((l) => l.status === "active");
        if (firstActive) {
          setSelectedPatient(firstActive);
        }
      }
    } catch (err) {
      console.error("Error loading doctor data:", err);
      setRosterError(err.message || "Failed to load patient roster");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDoctorData();
  }, [doctorId]);

  // Load Patient Workspace data whenever selectedPatient changes
  async function loadPatientWorkspace(patient) {
    if (!patient || !patient.patient_id) return;
    try {
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      const pId = patient.patient_id;
      const [meds, inters, outcomes, consents, encounters] = await Promise.all([
        getMedications(pId).catch(() => []),
        getInteractions(pId).catch(() => []),
        getPatientEffectiveness(pId).catch(() => []),
        getPatientConsents(pId).catch(() => []),
        getPatientEncounters(pId).catch(() => []),
      ]);

      setPatientMeds(meds || []);
      setPatientInteractions(inters || []);
      setPatientOutcomes(outcomes || []);
      setPatientConsents(consents || []);
      setPatientEncounters(encounters || []);

      // Check if an encounter is currently active
      const activeEnc = (encounters || [])
        .filter((e) => e.status === "active")
        .sort((a, b) => new Date(b.created_at || b.expires_at) - new Date(a.created_at || a.expires_at))[0];

      setActiveEncounter(activeEnc || null);
    } catch (err) {
      console.error("Error loading patient workspace:", err);
      setWorkspaceError(err.message || "Failed to load patient workspace");
    } finally {
      setWorkspaceLoading(false);
    }
  }

  useEffect(() => {
    if (selectedPatient) {
      loadPatientWorkspace(selectedPatient);
    }
  }, [selectedPatient]);

  // Live encounter countdown derived from activeEncounter.expires_at
  useEffect(() => {
    if (!activeEncounter || !activeEncounter.expires_at) {
      setCountdownSeconds(0);
      setIsEncounterExpired(false);
      return;
    }

    const checkTimer = () => {
      const expiresMs = new Date(activeEncounter.expires_at).getTime();
      const nowMs = Date.now();
      const remainingSec = Math.max(0, Math.floor((expiresMs - nowMs) / 1000));
      setCountdownSeconds(remainingSec);
      setIsEncounterExpired(remainingSec <= 0);
    };

    checkTimer();
    const interval = setInterval(checkTimer, 1000);
    return () => clearInterval(interval);
  }, [activeEncounter?.id, activeEncounter?.expires_at]);

  // When countdown transitions to zero, refresh encounter state
  const prevRemainingRef = useRef(countdownSeconds);
  useEffect(() => {
    if (prevRemainingRef.current > 0 && countdownSeconds === 0 && activeEncounter && selectedPatient) {
      loadPatientWorkspace(selectedPatient);
    }
    prevRemainingRef.current = countdownSeconds;
  }, [countdownSeconds, activeEncounter, selectedPatient]);

  // Small form: Request Access
  async function handleRequestAccess(e) {
    e.preventDefault();
    if (!requestEmail) return;
    setRequestResult(null);
    setActionLoading((prev) => ({ ...prev, requestAccess: true }));
    try {
      await requestLink(requestEmail);
      setRequestResult({
        type: "success",
        message: "pending (Awaiting patient approval)",
      });
      setRequestEmail("");
      await loadDoctorData();
    } catch (err) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("not found")) {
        setRequestResult({ type: "error", message: "patient not found" });
      } else if (
        msg.toLowerCase().includes("already requested") ||
        msg.toLowerCase().includes("active")
      ) {
        setRequestResult({ type: "warning", message: "already requested" });
      } else {
        setRequestResult({ type: "error", message: msg || "Failed to request link." });
      }
    } finally {
      setActionLoading((prev) => ({ ...prev, requestAccess: false }));
    }
  }

  // Request Link Modal
  async function handleConnectPatient(e) {
    e.preventDefault();
    setActionLoading((prev) => ({ ...prev, connectPatient: true }));
    try {
      await requestLink(connectEmail);
      showNotification(`Link request sent to ${connectEmail}! Awaiting patient approval.`);
      setConnectEmail("");
      setShowConnectModal(false);
      loadDoctorData();
    } catch (err) {
      showNotification(err.message || "Failed to send link request", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, connectPatient: false }));
    }
  }

  // Start Encounter
  async function handleStartEncounter(e) {
    e.preventDefault();
    if (!selectedPatient) return;
    setActionLoading((prev) => ({ ...prev, startEncounter: true }));
    try {
      const enc = await startEncounter(selectedPatient.patient_id, Number(encounterDuration));
      setActiveEncounter(enc);
      setIsEncounterExpired(false);
      setShowStartEncounterModal(false);
      showNotification(`Clinical Encounter initiated (${encounterDuration} min session window).`);
      loadPatientWorkspace(selectedPatient);
    } catch (err) {
      showNotification(err.message || "Cannot start encounter without active consent", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, startEncounter: false }));
    }
  }

  // Close Encounter
  async function handleCloseEncounter() {
    if (!activeEncounter) return;
    setActionLoading((prev) => ({ ...prev, closeEncounter: true }));
    try {
      await closeEncounter(activeEncounter.id);
      setActiveEncounter(null);
      setIsEncounterExpired(false);
      showNotification("Clinical encounter closed.");
      loadPatientWorkspace(selectedPatient);
    } catch (err) {
      showNotification(err.message || "Failed to close encounter", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, closeEncounter: false }));
    }
  }

  // Prescribe Medication
  async function handlePrescribeMedication(e) {
    e.preventDefault();
    if (!selectedPatient || !activeEncounter || isEncounterExpired) {
      showNotification("Cannot prescribe: Encounter is expired or inactive", "danger");
      return;
    }

    setActionLoading((prev) => ({ ...prev, prescribe: true }));
    try {
      const created = await addMedication({
        patient_id: selectedPatient.patient_id,
        encounter_id: activeEncounter.id,
        medication_name: prescriptionData.medication_name,
        dosage: prescriptionData.dosage || null,
        frequency: prescriptionData.frequency || null,
        notes: prescriptionData.notes || null,
        is_active: true,
      });

      setShowPrescribeModal(false);
      setPrescriptionData({ medication_name: "", dosage: "", frequency: "", notes: "" });

      if (created.interaction_flags && created.interaction_flags.length > 0) {
        setInteractionAlert(created.interaction_flags);
        showNotification(
          `WARNING: Multi-doctor drug safety conflict triggered! (${created.interaction_flags.length} flag)`,
          "danger"
        );
      } else {
        showNotification("Prescription recorded successfully with 0 interaction flags.");
      }

      loadPatientWorkspace(selectedPatient);
    } catch (err) {
      showNotification(err.message || "Failed to prescribe medication", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, prescribe: false }));
    }
  }

  const activeLinks = links.filter((l) => l.status === "active");
  const visibleLinks = links.filter((l) => l.status === "active" || l.status === "pending");
  const filteredPatients = visibleLinks.filter((l) =>
    (l.patient_name || l.patient_email || "")
      .toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

  const hasActiveConsent = (patientConsents || []).some(
    (c) => c.doctor_id === doctorId && c.is_active
  );

  return (
    <>
      <Navbar />

      <main className="dashboard-container">
        {statusMessage.text && (
          <div
            className={`alert-interaction`}
            style={{
              borderColor: statusMessage.type === "danger" ? "#ef4444" : statusMessage.type === "warning" ? "#f59e0b" : "#10b981",
              background: statusMessage.type === "danger" ? "rgba(239, 68, 68, 0.15)" : statusMessage.type === "warning" ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.15)",
              animation: "none",
              marginBottom: "1.5rem",
            }}
          >
            <Activity size={20} color={statusMessage.type === "danger" ? "#ef4444" : statusMessage.type === "warning" ? "#f59e0b" : "#10b981"} />
            <div style={{ flex: 1, fontSize: "0.9rem" }}>{statusMessage.text}</div>
          </div>
        )}

        {/* Real-time Interaction Warning Modal / Alert */}
        {interactionAlert && (
          <div
            className="alert-interaction"
            style={{
              marginBottom: "2rem",
              background: "rgba(239, 68, 68, 0.2)",
              border: "2px solid #ef4444",
            }}
          >
            <AlertTriangle size={28} color="#ef4444" style={{ flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ color: "#fff", marginBottom: "0.3rem" }}>
                CRITICAL CLINICAL ALERT: Drug-Drug Interaction Detected!
              </h3>
              {interactionAlert.map((f, i) => (
                <div key={i} style={{ marginTop: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className="alert-severity-tag">{f.severity} SEVERITY</span>
                    <strong>{f.medication_a_name} ↔ {f.medication_b_name}</strong>
                  </div>
                  <p style={{ color: "#fca5a5", fontSize: "0.875rem", marginTop: "0.25rem" }}>
                    {f.description}
                  </p>
                </div>
              ))}
            </div>
            <button
              onClick={() => setInteractionAlert(null)}
              className="btn btn-secondary btn-sm"
            >
              Acknowledge
            </button>
          </div>
        )}

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1>Clinical Care Workspace</h1>
            <p className="page-subtitle">
              Consent-verified patient management • Cross-doctor interaction safety
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              onClick={() => setShowConnectModal(true)}
              className="btn btn-primary"
            >
              <Send size={18} />
              <span>Connect Patient</span>
            </button>
            <button
              onClick={loadDoctorData}
              className="btn btn-secondary"
              disabled={refreshing}
            >
              <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* Quick Metrics */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon-box cyan">
              <Users size={24} />
            </div>
            <div>
              <div className="metric-value">{activeLinks.length}</div>
              <div className="metric-label">Linked Patients</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box teal">
              <Clock size={24} />
            </div>
            <div>
              <div className="metric-value">{activeEncounter ? "Active" : "Idle"}</div>
              <div className="metric-label">Encounter Session</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box purple">
              <Pill size={24} />
            </div>
            <div>
              <div className="metric-value">{patientMeds.length}</div>
              <div className="metric-label">Total Patient Meds</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box amber">
              <ShieldAlert size={24} />
            </div>
            <div>
              <div className="metric-value">{patientInteractions.length}</div>
              <div className="metric-label">Safety Conflicts</div>
            </div>
          </div>
        </div>

        {/* Two Column Layout: Patient Selector (Left) + Clinical Chart (Right) */}
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "1.75rem", alignItems: "start" }}>
          
          {/* LEFT: Patient Roster */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <Users size={18} color="var(--accent-cyan-light)" />
              <h3 style={{ fontSize: "1.05rem" }}>Patient Roster</h3>
            </div>

            {/* Small Form: patient email -> "Request access" */}
            <form onSubmit={handleRequestAccess} style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="email"
                  className="form-input"
                  placeholder="Patient email..."
                  style={{ fontSize: "0.85rem", padding: "0.45rem 0.65rem", flex: 1 }}
                  value={requestEmail}
                  onChange={(e) => setRequestEmail(e.target.value)}
                  required
                />
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  style={{ whiteSpace: "nowrap" }}
                  disabled={actionLoading.requestAccess}
                >
                  {actionLoading.requestAccess ? "Requesting..." : "Request access"}
                </button>
              </div>
              {requestResult && (
                <div
                  style={{
                    marginTop: "0.5rem",
                    fontSize: "0.78rem",
                    padding: "0.35rem 0.55rem",
                    borderRadius: "var(--radius-sm)",
                    color:
                      requestResult.type === "success"
                        ? "#6ee7b7"
                        : requestResult.type === "warning"
                        ? "#fcd34d"
                        : "#fca5a5",
                    background:
                      requestResult.type === "success"
                        ? "rgba(16, 185, 129, 0.15)"
                        : requestResult.type === "warning"
                        ? "rgba(245, 158, 11, 0.15)"
                        : "rgba(239, 68, 68, 0.15)",
                    border: `1px solid ${
                      requestResult.type === "success"
                        ? "#10b981"
                        : requestResult.type === "warning"
                        ? "#f59e0b"
                        : "#ef4444"
                    }`,
                  }}
                >
                  {requestResult.message}
                </div>
              )}
            </form>

            <div style={{ position: "relative", marginBottom: "1rem" }}>
              <input
                type="text"
                className="form-input"
                placeholder="Search roster..."
                style={{ paddingLeft: "2.25rem", fontSize: "0.85rem" }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)" }}
              />
            </div>

            {rosterError && (
              <div
                className="alert-interaction"
                style={{
                  borderColor: "#ef4444",
                  background: "rgba(239, 68, 68, 0.15)",
                  padding: "0.6rem 0.75rem",
                  marginBottom: "0.75rem",
                  animation: "none",
                }}
              >
                <div style={{ fontSize: "0.8rem", color: "#fca5a5", flex: 1 }}>{rosterError}</div>
                <button
                  type="button"
                  onClick={loadDoctorData}
                  className="btn btn-secondary btn-sm"
                  style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                >
                  Retry
                </button>
              </div>
            )}

            {loading ? (
              <div style={{ textAlign: "center", padding: "1rem", color: "var(--text-muted)" }}>
                Loading patients...
              </div>
            ) : filteredPatients.length === 0 ? (
              <div style={{ textAlign: "center", padding: "1.5rem 0.5rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                No connected patients. Use the form above to request access.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {filteredPatients.map((link) => {
                  const isPending = link.status === "pending";
                  const isSelected = selectedPatient?.id === link.id;
                  return (
                    <div
                      key={link.id}
                      onClick={() => {
                        if (!isPending) setSelectedPatient(link);
                      }}
                      style={{
                        padding: "0.75rem 1rem",
                        borderRadius: "var(--radius-md)",
                        background: isSelected
                          ? "rgba(2, 132, 199, 0.2)"
                          : isPending
                          ? "rgba(31, 41, 55, 0.2)"
                          : "rgba(31, 41, 55, 0.4)",
                        border: isSelected
                          ? "1px solid var(--accent-cyan-light)"
                          : isPending
                          ? "1px dashed rgba(148, 163, 184, 0.35)"
                          : "1px solid var(--border-subtle)",
                        cursor: isPending ? "default" : "pointer",
                        transition: "all 0.2s ease",
                        opacity: isPending ? 0.85 : 1,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                        <div style={{ fontWeight: 600, color: isPending ? "#cbd5e1" : "#fff", fontSize: "0.95rem" }}>
                          {link.patient_name || link.patient_email}
                        </div>
                        {isPending && (
                          <span
                            className="badge"
                            style={{
                              fontSize: "0.68rem",
                              background: "rgba(245, 158, 11, 0.15)",
                              color: "#fbbf24",
                              border: "1px solid rgba(245, 158, 11, 0.35)",
                              whiteSpace: "nowrap",
                            }}
                          >
                            Awaiting patient approval
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.15rem" }}>
                        {link.patient_email}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* RIGHT: Patient Clinical Chart & Encounter Workspace */}
          {selectedPatient ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              {workspaceError && (
                <div
                  className="alert-interaction"
                  style={{
                    borderColor: "#ef4444",
                    background: "rgba(239, 68, 68, 0.15)",
                    animation: "none",
                  }}
                >
                  <AlertTriangle size={20} color="#ef4444" />
                  <div style={{ flex: 1, color: "#fca5a5", fontSize: "0.875rem" }}>{workspaceError}</div>
                  <button
                    type="button"
                    onClick={() => loadPatientWorkspace(selectedPatient)}
                    className="btn btn-secondary btn-sm"
                  >
                    Retry
                  </button>
                </div>
              )}

              {workspaceLoading && (
                <div className="card empty-state" style={{ padding: "1.25rem" }}>
                  <Activity size={24} className="animate-spin" style={{ margin: "0 auto 0.5rem", color: "var(--accent-cyan-light)" }} />
                  <div>Loading patient chart & clinical telemetry...</div>
                </div>
              )}
              
              {/* Encounter Status Banner */}
              {activeEncounter ? (
                <div
                  className="encounter-banner"
                  style={
                    isEncounterExpired
                      ? {
                          borderColor: "rgba(239, 68, 68, 0.5)",
                          background: "rgba(239, 68, 68, 0.12)",
                        }
                      : {}
                  }
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <div
                      className={isEncounterExpired ? "" : "encounter-pulse"}
                      style={
                        isEncounterExpired
                          ? { width: 12, height: 12, borderRadius: "50%", background: "#ef4444" }
                          : {}
                      }
                    />
                    <div>
                      <div style={{ fontWeight: 700, color: "#fff", fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span>Clinical Encounter Session</span>
                        {isEncounterExpired ? (
                          <span className="badge badge-danger">Encounter expired</span>
                        ) : (
                          <span className="badge badge-active" style={{ fontSize: "0.75rem" }}>
                            ⏱ {formatCountdown(countdownSeconds)}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: "0.8rem", color: isEncounterExpired ? "#fca5a5" : "var(--text-secondary)" }}>
                        {isEncounterExpired
                          ? "Encounter session window expired. Prescription pad is locked. Please close session."
                          : `Session open until: ${new Date(activeEncounter.expires_at).toLocaleTimeString()} (${formatCountdown(countdownSeconds)} remaining)`}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.75rem" }}>
                    <button
                      onClick={() => setShowPrescribeModal(true)}
                      className="btn btn-primary btn-sm"
                      disabled={isEncounterExpired || actionLoading.prescribe}
                      title={isEncounterExpired ? "Encounter expired" : "Prescribe Medication"}
                    >
                      <Plus size={16} />
                      <span>{isEncounterExpired ? "Encounter expired" : "Prescribe Medication"}</span>
                    </button>
                    <button
                      onClick={handleCloseEncounter}
                      className="btn btn-secondary btn-sm"
                      disabled={actionLoading.closeEncounter}
                    >
                      {actionLoading.closeEncounter ? "Closing..." : "Close Session"}
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    background: "rgba(31, 41, 55, 0.5)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-lg)",
                    padding: "1.25rem 1.5rem",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                      <h2 style={{ fontSize: "1.35rem" }}>
                        {selectedPatient.patient_name || "Patient"}
                      </h2>
                      <span className={`badge ${hasActiveConsent ? "badge-active" : "badge-danger"}`}>
                        {hasActiveConsent ? "Consent Active" : "No Active Consent"}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                      {selectedPatient.patient_email} • Record Sovereignty Maintained
                    </div>
                  </div>

                  <div>
                    {hasActiveConsent ? (
                      <button
                        onClick={() => setShowStartEncounterModal(true)}
                        className="btn btn-primary btn-sm"
                        disabled={actionLoading.startEncounter}
                      >
                        <Clock size={16} />
                        <span>Start Clinical Encounter</span>
                      </button>
                    ) : (
                      <div style={{ fontSize: "0.85rem", color: "#f87171" }}>
                        Patient must grant consent before encounter can start.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Medication History & Multi-Doctor Safety */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <Pill size={20} color="var(--accent-teal-light)" />
                    Patient's Unified Medication History (Cross-Doctor)
                  </h3>
                  {activeEncounter && (
                    <button
                      onClick={() => setShowPrescribeModal(true)}
                      className={isEncounterExpired ? "btn btn-secondary btn-sm" : "btn btn-primary btn-sm"}
                      disabled={isEncounterExpired || actionLoading.prescribe}
                      title={isEncounterExpired ? "Encounter expired" : "Prescribe"}
                    >
                      <Plus size={16} />
                      <span>{isEncounterExpired ? "Encounter expired" : "Prescribe"}</span>
                    </button>
                  )}
                </div>

                {patientMeds.length === 0 ? (
                  <div className="empty-state">No medications on record for this patient.</div>
                ) : (
                  <div>
                    {patientMeds.map((med) => (
                      <div key={med.id} className="med-item">
                        <div className="med-header">
                          <div>
                            <div className="med-name">
                              {med.medication_name}
                              <span className={`badge ${med.is_active ? "badge-active" : "badge-inactive"}`}>
                                {med.is_active ? "Active" : "Discontinued"}
                              </span>
                            </div>
                            <div className="med-meta">
                              {med.dosage && <span><strong>Dosage:</strong> {med.dosage}</span>}
                              {med.frequency && <span><strong>Frequency:</strong> {med.frequency}</span>}
                              <span>
                                Prescribed by: {med.doctor_id === doctorId ? "You" : med.doctor_id ? "External Doctor" : "Self-Reported"}
                              </span>
                              <span>
                                Started: {new Date(med.start_date || med.created_at).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </div>

                        {med.notes && (
                          <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                            <strong>Instructions:</strong> {med.notes}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Safety & Drug Interactions */}
              {patientInteractions.length > 0 ? (
                <div className="card" style={{ borderColor: "rgba(239, 68, 68, 0.4)" }}>
                  <div className="card-header">
                    <h3 className="card-title" style={{ color: "#ef4444" }}>
                      <AlertTriangle size={20} />
                      Cross-Doctor Adverse Drug Interaction Alerts
                    </h3>
                  </div>

                  <div>
                    {patientInteractions.map((flag) => (
                      <div key={flag.id} className="alert-interaction" style={{ marginBottom: "0.75rem" }}>
                        <AlertTriangle size={22} color="#ef4444" style={{ flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                            <span className="alert-severity-tag">{flag.severity}</span>
                            <strong>{flag.medication_a_name} ↔ {flag.medication_b_name}</strong>
                          </div>
                          <p style={{ color: "#fca5a5", fontSize: "0.85rem", marginTop: "0.25rem" }}>
                            {flag.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">
                      <CheckCircle size={20} color="#10b981" />
                      Cross-Doctor Drug Interaction Safety
                    </h3>
                  </div>
                  <div className="empty-state" style={{ padding: "1.25rem" }}>
                    No cross-doctor adverse drug interaction conflicts detected for this patient.
                  </div>
                </div>
              )}

              {/* Patient Reported Outcomes */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <HeartPulse size={20} color="#ec4899" />
                    Patient-Reported Telemetry & Side Effects
                  </h3>
                </div>

                {patientOutcomes.length === 0 ? (
                  <div className="empty-state">No outcome telemetry reported by this patient yet.</div>
                ) : (
                  <div>
                    {patientOutcomes.map((log) => (
                      <div key={log.id} className="med-item">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <h4>{log.medication_name || "Medication"}</h4>
                          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                            {new Date(log.logged_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: "0.35rem 0" }}>
                          <span style={{ color: "#fbbf24", fontWeight: 700 }}>
                            {"★".repeat(log.rating)}{"☆".repeat(5 - log.rating)}
                          </span>
                          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                            ({log.rating}/5 Effectiveness)
                          </span>
                        </div>
                        {log.side_effects && (
                          <div style={{ fontSize: "0.85rem", color: "#fca5a5", marginTop: "0.25rem" }}>
                            <strong>Side Effects Reported:</strong> {log.side_effects}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="card empty-state">
              <Users size={48} className="empty-icon" />
              <h3>Select a Patient</h3>
              <p>Choose a patient from the roster or connect a new patient by email.</p>
            </div>
          )}
        </div>
      </main>

      {/* MODAL: CONNECT PATIENT */}
      {showConnectModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Connect New Patient</h3>
              <button onClick={() => setShowConnectModal(false)} className="btn btn-sm btn-secondary">
                ✕
              </button>
            </div>

            <form onSubmit={handleConnectPatient}>
              <p style={{ fontSize: "0.875rem", marginBottom: "1.25rem" }}>
                Send a cryptographic link request to a patient's registered email. Once approved, you can request clinical encounter sessions.
              </p>

              <div className="form-group">
                <label className="form-label">Patient Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="patient@example.com"
                  value={connectEmail}
                  onChange={(e) => setConnectEmail(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowConnectModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionLoading.connectPatient}
                >
                  {actionLoading.connectPatient ? "Sending..." : "Send Connection Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: START ENCOUNTER */}
      {showStartEncounterModal && selectedPatient && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Start Clinical Encounter</h3>
              <button onClick={() => setShowStartEncounterModal(false)} className="btn btn-sm btn-secondary">
                ✕
              </button>
            </div>

            <form onSubmit={handleStartEncounter}>
              <p style={{ fontSize: "0.875rem", marginBottom: "1.25rem" }}>
                Starting an encounter opens a secure write session to prescribe medications and consult with <strong>{selectedPatient.patient_name || selectedPatient.patient_email}</strong>.
              </p>

              <div className="form-group">
                <label className="form-label">Session Window Duration</label>
                <select
                  className="form-select"
                  value={encounterDuration}
                  onChange={(e) => setEncounterDuration(e.target.value)}
                >
                  <option value={15}>15 Minutes (Brief Follow-up)</option>
                  <option value={30}>30 Minutes (Standard Consultation)</option>
                  <option value={60}>60 Minutes (Comprehensive Visit)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowStartEncounterModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionLoading.startEncounter}
                >
                  {actionLoading.startEncounter ? "Initiating..." : "Initiate Encounter"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: PRESCRIBE MEDICATION */}
      {showPrescribeModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Prescribe Medication</h3>
              <button onClick={() => setShowPrescribeModal(false)} className="btn btn-sm btn-secondary">
                ✕
              </button>
            </div>

            <form onSubmit={handlePrescribeMedication}>
              {isEncounterExpired && (
                <div
                  className="alert-interaction"
                  style={{
                    borderColor: "#ef4444",
                    background: "rgba(239, 68, 68, 0.15)",
                    marginBottom: "1rem",
                    animation: "none",
                  }}
                >
                  <AlertTriangle size={18} color="#ef4444" />
                  <div style={{ fontSize: "0.875rem", color: "#fca5a5" }}>
                    Encounter expired. The prescription pad is locked. Please close this session and start a new encounter.
                  </div>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Drug / Compound Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Warfarin, Aspirin 81mg, Amoxicillin 500mg, Lisinopril"
                  value={prescriptionData.medication_name}
                  onChange={(e) => setPrescriptionData({ ...prescriptionData, medication_name: e.target.value })}
                  required
                  disabled={isEncounterExpired}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Dosage</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. 5mg, 81mg, 1 tablet"
                    value={prescriptionData.dosage}
                    onChange={(e) => setPrescriptionData({ ...prescriptionData, dosage: e.target.value })}
                    disabled={isEncounterExpired}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Frequency</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Once daily at bedtime"
                    value={prescriptionData.frequency}
                    onChange={(e) => setPrescriptionData({ ...prescriptionData, frequency: e.target.value })}
                    disabled={isEncounterExpired}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Clinical Instructions & Directions</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="Special instructions, dietary warnings, target symptoms..."
                  value={prescriptionData.notes}
                  onChange={(e) => setPrescriptionData({ ...prescriptionData, notes: e.target.value })}
                  disabled={isEncounterExpired}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowPrescribeModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isEncounterExpired || actionLoading.prescribe}
                >
                  {isEncounterExpired
                    ? "Encounter expired"
                    : actionLoading.prescribe
                    ? "Prescribing..."
                    : "Authorize & Issue Prescription"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}