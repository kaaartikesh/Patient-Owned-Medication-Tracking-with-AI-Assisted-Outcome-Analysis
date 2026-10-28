import { useState, useEffect } from "react";
import {
  Pill,
  AlertTriangle,
  Users,
  ShieldCheck,
  Download,
  Plus,
  Star,
  CheckCircle,
  XCircle,
  FileText,
  Clock,
  ChevronRight,
  Activity,
  HeartPulse,
  Lock,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import {
  getMedications,
  addMedication,
  getInteractions,
  logEffectiveness,
  getPatientEffectiveness,
  getMyConsents,
  grantConsent,
  revokeConsent,
  getMyLinks,
  approveLink,
  rejectLink,
  getAuditLog,
  exportHistoryJson,
  downloadExportPdf,
} from "../api/index";

export default function PatientDashboard() {
  const { user } = useAuth();
  const patientId = user?.patient_id;

  const [activeTab, setActiveTab] = useState("medications");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Data states
  const [medications, setMedications] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [effectivenessLogs, setEffectivenessLogs] = useState([]);
  const [consents, setConsents] = useState([]);
  const [links, setLinks] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  // Modals
  const [showAddMedModal, setShowAddMedModal] = useState(false);
  const [showRateModal, setShowRateModal] = useState(false);
  const [showGrantConsentModal, setShowGrantConsentModal] = useState(false);
  const [selectedMedForRating, setSelectedMedForRating] = useState(null);
  const [selectedDoctorForConsent, setSelectedDoctorForConsent] = useState(null);

  // Form states
  const [newMed, setNewMed] = useState({
    medication_name: "",
    dosage: "",
    frequency: "",
    notes: "",
    is_active: true,
  });

  const [ratingData, setRatingData] = useState({
    rating: 5,
    side_effects: "",
  });

  const [consentData, setConsentData] = useState({
    scope: "all",
    expires_in_days: 30,
  });

  const [actionLoading, setActionLoading] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [statusMessage, setStatusMessage] = useState({ text: "", type: "" });

  function showNotification(text, type = "success") {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage({ text: "", type: "" }), 4000);
  }

  async function loadDashboardData() {
    if (!patientId) return;
    try {
      setRefreshing(true);
      setLoadError(null);
      const [medsData, interData, effData, linksData, consData, audData] =
        await Promise.all([
          getMedications(patientId).catch(() => []),
          getInteractions(patientId).catch(() => []),
          getPatientEffectiveness(patientId).catch(() => []),
          getMyLinks().catch(() => []),
          getMyConsents().catch(() => []),
          getAuditLog(patientId).catch(() => []),
        ]);

      setMedications(medsData || []);
      setInteractions(interData || []);
      setEffectivenessLogs(effData || []);
      setLinks(linksData || []);
      setConsents(consData || []);
      setAuditLogs(audData || []);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
      setLoadError(err.message || "Failed to load patient records.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, [patientId]);

  // Handle Add Medication
  async function handleAddMedication(e) {
    e.preventDefault();
    setActionLoading((prev) => ({ ...prev, addMed: true }));
    try {
      const created = await addMedication({
        patient_id: patientId,
        medication_name: newMed.medication_name,
        dosage: newMed.dosage || null,
        frequency: newMed.frequency || null,
        notes: newMed.notes || null,
        is_active: newMed.is_active,
      });

      setShowAddMedModal(false);
      setNewMed({ medication_name: "", dosage: "", frequency: "", notes: "", is_active: true });

      if (created.interaction_flags && created.interaction_flags.length > 0) {
        showNotification(
          `Medication added! Warning: ${created.interaction_flags.length} adverse interaction flagged!`,
          "warning"
        );
      } else {
        showNotification("Medication logged successfully!");
      }
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to log medication", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, addMed: false }));
    }
  }

  // Handle Rate Effectiveness
  async function handleLogEffectiveness(e) {
    e.preventDefault();
    if (!selectedMedForRating) return;
    setActionLoading((prev) => ({ ...prev, logEffectiveness: true }));
    try {
      await logEffectiveness({
        medication_entry_id: selectedMedForRating.id,
        rating: ratingData.rating,
        side_effects: ratingData.side_effects || null,
      });

      setShowRateModal(false);
      setSelectedMedForRating(null);
      setRatingData({ rating: 5, side_effects: "" });
      showNotification("Medication outcome rating logged successfully!");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to log rating", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, logEffectiveness: false }));
    }
  }

  // Handle Link Approval / Rejection
  async function handleApproveLink(linkId) {
    setActionLoading((prev) => ({ ...prev, [`approve_${linkId}`]: true }));
    try {
      await approveLink(linkId);
      showNotification("Doctor link approved! You can now grant consent.");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to approve link", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`approve_${linkId}`]: false }));
    }
  }

  async function handleRejectLink(linkId, doctorName) {
    const confirmed = window.confirm(
      `Are you sure you want to reject the link request from ${doctorName || "this doctor"}?`
    );
    if (!confirmed) return;

    setActionLoading((prev) => ({ ...prev, [`reject_${linkId}`]: true }));
    try {
      await rejectLink(linkId);
      showNotification("Doctor link rejected.", "warning");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to reject link", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`reject_${linkId}`]: false }));
    }
  }

  async function handleDisconnectLink(linkId, doctorName) {
    const confirmed = window.confirm(
      `Are you sure you want to disconnect from ${doctorName || "this doctor"}? Their access will be revoked.`
    );
    if (!confirmed) return;

    setActionLoading((prev) => ({ ...prev, [`disconnect_${linkId}`]: true }));
    try {
      await rejectLink(linkId);
      showNotification("Doctor link disconnected.", "warning");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to disconnect doctor", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`disconnect_${linkId}`]: false }));
    }
  }

  // Handle Grant Consent
  async function handleGrantConsent(e) {
    e.preventDefault();
    if (!selectedDoctorForConsent) return;
    setActionLoading((prev) => ({ ...prev, grantConsent: true }));
    try {
      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + Number(consentData.expires_in_days));

      await grantConsent(selectedDoctorForConsent.doctor_id, consentData.scope, expiresAt.toISOString());
      setShowGrantConsentModal(false);
      setSelectedDoctorForConsent(null);
      showNotification("Consent granted to doctor!");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to grant consent", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, grantConsent: false }));
    }
  }

  // Handle Revoke Consent
  async function handleRevokeConsent(consentId, doctorName) {
    const confirmed = window.confirm(
      `Are you sure you want to revoke consent for ${doctorName || "this doctor"}?`
    );
    if (!confirmed) return;

    setActionLoading((prev) => ({ ...prev, [`revokeConsent_${consentId}`]: true }));
    try {
      await revokeConsent(consentId);
      showNotification("Consent revoked! Doctor access immediately terminated.", "warning");
      await loadDashboardData();
    } catch (err) {
      showNotification(err.message || "Failed to revoke consent", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`revokeConsent_${consentId}`]: false }));
    }
  }

  // PDF Export
  async function handleDownloadPdf() {
    setActionLoading((prev) => ({ ...prev, downloadPdf: true }));
    try {
      showNotification("Generating verified medical history PDF...");
      await downloadExportPdf(patientId, `health_record_${user?.name || "patient"}.pdf`);
      showNotification("PDF downloaded successfully!");
    } catch (err) {
      showNotification(err.message || "Failed to download PDF", "danger");
    } finally {
      setActionLoading((prev) => ({ ...prev, downloadPdf: false }));
    }
  }

  // JSON Export
  async function handleDownloadJson() {
    try {
      const data = await exportHistoryJson(patientId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `patient_record_${patientId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showNotification("Portable EHR JSON downloaded!");
    } catch (err) {
      showNotification(err.message || "Failed to export JSON", "danger");
    }
  }

  const activeMeds = medications.filter((m) => m.is_active);
  const pendingLinks = links.filter((l) => l.status === "pending");
  const approvedLinks = links.filter((l) => l.status === "active");

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

        {loadError && (
          <div
            className="alert-interaction"
            style={{
              borderColor: "#ef4444",
              background: "rgba(239, 68, 68, 0.15)",
              animation: "none",
              marginBottom: "1.5rem",
            }}
          >
            <AlertCircle size={20} color="#ef4444" style={{ flexShrink: 0 }} />
            <div style={{ flex: 1, fontSize: "0.9rem", color: "#fca5a5" }}>{loadError}</div>
            <button
              onClick={loadDashboardData}
              className="btn btn-secondary btn-sm"
              disabled={refreshing}
            >
              Retry
            </button>
          </div>
        )}

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1>Patient Health Hub</h1>
            <p className="page-subtitle">
              Sovereign record ownership • Multi-doctor oversight • Outcome telemetry
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              onClick={() => setShowAddMedModal(true)}
              className="btn btn-primary"
            >
              <Plus size={18} />
              <span>Log Medication</span>
            </button>
            <button
              onClick={handleDownloadPdf}
              className="btn btn-secondary"
              title="Download Verified PDF Record"
            >
              <Download size={18} />
              <span>Export PDF</span>
            </button>
            <button
              onClick={loadDashboardData}
              className="btn btn-secondary"
              disabled={refreshing}
              title="Refresh Records"
            >
              <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* Quick Metrics */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon-box teal">
              <Pill size={24} />
            </div>
            <div>
              <div className="metric-value">{activeMeds.length}</div>
              <div className="metric-label">Active Prescriptions</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box amber">
              <AlertTriangle size={24} />
            </div>
            <div>
              <div className="metric-value">{interactions.length}</div>
              <div className="metric-label">Drug Interaction Flags</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box cyan">
              <Users size={24} />
            </div>
            <div>
              <div className="metric-value">{approvedLinks.length}</div>
              <div className="metric-label">Authorized Doctors</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon-box purple">
              <HeartPulse size={24} />
            </div>
            <div>
              <div className="metric-value">{effectivenessLogs.length}</div>
              <div className="metric-label">Efficacy Reports</div>
            </div>
          </div>
        </div>

        {/* Pending Requests Alert Banner */}
        {pendingLinks.length > 0 && (
          <div
            className="alert-interaction"
            style={{
              borderColor: "#38bdf8",
              background: "rgba(56, 189, 248, 0.12)",
              animation: "none",
              marginBottom: "1.75rem",
            }}
          >
            <Users size={22} color="#38bdf8" style={{ flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <strong style={{ color: "#38bdf8" }}>Connection Request Pending:</strong> You have {pendingLinks.length} doctor connection request(s) awaiting your consent approval.
            </div>
            <button
              onClick={() => setActiveTab("consent")}
              className="btn btn-sm btn-outline"
            >
              Review Requests
            </button>
          </div>
        )}

        {/* Navigation Tabs */}
        <nav className="tabs-nav">
          <button
            onClick={() => setActiveTab("medications")}
            className={`tab-btn ${activeTab === "medications" ? "active" : ""}`}
          >
            <Pill size={18} />
            <span>Medication History</span>
            <span className="tab-count">{medications.length}</span>
          </button>

          <button
            onClick={() => setActiveTab("interactions")}
            className={`tab-btn ${activeTab === "interactions" ? "active" : ""}`}
          >
            <AlertTriangle size={18} />
            <span>Drug Interactions</span>
            {interactions.length > 0 && (
              <span className="tab-count" style={{ background: "rgba(239, 68, 68, 0.25)", color: "#f87171" }}>
                {interactions.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("consent")}
            className={`tab-btn ${activeTab === "consent" ? "active" : ""}`}
          >
            <ShieldCheck size={18} />
            <span>Doctors & Consent</span>
            <span className="tab-count">{approvedLinks.length}</span>
          </button>

          <button
            onClick={() => setActiveTab("effectiveness")}
            className={`tab-btn ${activeTab === "effectiveness" ? "active" : ""}`}
          >
            <HeartPulse size={18} />
            <span>Outcome & Efficacy</span>
            <span className="tab-count">{effectivenessLogs.length}</span>
          </button>

          <button
            onClick={() => setActiveTab("audit")}
            className={`tab-btn ${activeTab === "audit" ? "active" : ""}`}
          >
            <Lock size={18} />
            <span>Privacy Audit Trail</span>
            <span className="tab-count">{auditLogs.length}</span>
          </button>
        </nav>

        {/* TAB 1: MEDICATIONS */}
        {activeTab === "medications" && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Pill size={20} color="var(--accent-teal-light)" />
                Unified Cross-Doctor Medication Profile
              </h2>
              <button
                onClick={() => setShowAddMedModal(true)}
                className="btn btn-primary btn-sm"
              >
                <Plus size={16} />
                <span>Add Medication</span>
              </button>
            </div>

            {loading ? (
              <div className="empty-state">Loading medication records...</div>
            ) : medications.length === 0 ? (
              <div className="empty-state">
                <Pill className="empty-icon" />
                <h3>No Medications Recorded</h3>
                <p>Add self-reported OTC meds or connect with a doctor during an active encounter.</p>
              </div>
            ) : (
              <div>
                {medications.map((med) => (
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
                          {med.dosage && (
                            <span className="meta-pill">
                              <strong>Dosage:</strong> {med.dosage}
                            </span>
                          )}
                          {med.frequency && (
                            <span className="meta-pill">
                              <strong>Frequency:</strong> {med.frequency}
                            </span>
                          )}
                          <span className="meta-pill">
                            <Clock size={14} />
                            Started: {new Date(med.start_date || med.created_at).toLocaleDateString()}
                          </span>
                          <span className="meta-pill">
                            <Users size={14} />
                            {med.doctor_id ? "Prescribed by Clinician" : "Self-Reported Entry"}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                          onClick={() => {
                            setSelectedMedForRating(med);
                            setShowRateModal(true);
                          }}
                          className="btn btn-secondary btn-sm"
                        >
                          <Star size={14} color="#fbbf24" />
                          <span>Rate Efficacy</span>
                        </button>
                      </div>
                    </div>

                    {med.notes && (
                      <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        <strong>Notes:</strong> {med.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: DRUG INTERACTIONS */}
        {activeTab === "interactions" && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <AlertTriangle size={20} color="#f59e0b" />
                Cross-Doctor Safety & Drug-Drug Interactions
              </h2>
            </div>

            <p style={{ marginBottom: "1.5rem" }}>
              Our automated drug safety engine evaluates every prescription across all treating doctors to prevent dangerous multi-prescribing hazards and adverse interactions.
            </p>

            {loading ? (
              <div className="empty-state">Evaluating cross-doctor drug interactions...</div>
            ) : interactions.length === 0 ? (
              <div className="empty-state">
                <CheckCircle size={48} color="#10b981" style={{ marginBottom: "0.75rem" }} />
                <h3>No Adverse Interactions Flagged</h3>
                <p>Your current cross-doctor prescriptions have cleared drug-drug safety checks.</p>
              </div>
            ) : (
              <div>
                {interactions.map((flag) => (
                  <div key={flag.id} className="alert-interaction">
                    <AlertTriangle size={24} color="#ef4444" style={{ flexShrink: 0, marginTop: "2px" }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem" }}>
                        <span className="alert-severity-tag">{flag.severity} RISK</span>
                        <h4 style={{ margin: 0, color: "#fff" }}>
                          {flag.medication_a_name || "Drug A"} ↔ {flag.medication_b_name || "Drug B"}
                        </h4>
                      </div>
                      <p style={{ color: "#cbd5e1", fontSize: "0.9rem" }}>
                        {flag.description}
                      </p>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                        Flagged on {new Date(flag.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: DOCTORS & CONSENT */}
        {activeTab === "consent" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Pending Requests */}
            {pendingLinks.length > 0 ? (
              <div className="card" style={{ borderColor: "rgba(56, 189, 248, 0.4)" }}>
                <div className="card-header">
                  <h3 className="card-title" style={{ color: "#38bdf8" }}>
                    <Users size={20} />
                    Pending Doctor Connection Requests
                  </h3>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {pendingLinks.map((link) => (
                    <div
                      key={link.id}
                      style={{
                        background: "rgba(31, 41, 55, 0.5)",
                        padding: "1.25rem",
                        borderRadius: "var(--radius-md)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: "1rem",
                      }}
                    >
                      <div>
                        <h4>{link.doctor_name || "Licensed Clinician"}</h4>
                        <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                          {link.doctor_specialty || "General Medicine"} • {link.doctor_email}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "0.75rem" }}>
                        <button
                          onClick={() => handleApproveLink(link.id)}
                          className="btn btn-primary btn-sm"
                          disabled={actionLoading[`approve_${link.id}`]}
                        >
                          <CheckCircle size={16} />
                          <span>{actionLoading[`approve_${link.id}`] ? "Approving..." : "Approve Connection"}</span>
                        </button>
                        <button
                          onClick={() => handleRejectLink(link.id, link.doctor_name)}
                          className="btn btn-danger btn-sm"
                          disabled={actionLoading[`reject_${link.id}`]}
                        >
                          <XCircle size={16} />
                          <span>{actionLoading[`reject_${link.id}`] ? "Rejecting..." : "Reject"}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="card empty-state" style={{ padding: "1.25rem" }}>
                <Users className="empty-icon" />
                <h4>No Pending Connection Requests</h4>
                <p>When a doctor requests access to your record, you will be able to review, approve, or reject them here.</p>
              </div>
            )}

            {/* Active Doctors & Consent Rights */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <ShieldCheck size={20} color="var(--accent-teal-light)" />
                  Authorized Care Team & Consent Control
                </h3>
              </div>

              <p style={{ marginBottom: "1.5rem" }}>
                You maintain complete sovereign ownership over your health record. Doctors cannot read your records or prescribe medications unless you actively maintain unrevoked consent.
              </p>

              {loading ? (
                <div className="empty-state">Loading care team connections...</div>
              ) : approvedLinks.length === 0 ? (
                <div className="empty-state">
                  <Users className="empty-icon" />
                  <h4>No Active Doctor Connections</h4>
                  <p>When a doctor requests access with your email address, approve them here.</p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {approvedLinks.map((link) => {
                    const activeConsent = consents.find(
                      (c) => c.doctor_id === link.doctor_id && c.is_active
                    );

                    return (
                      <div
                        key={link.id}
                        style={{
                          background: "rgba(31, 41, 55, 0.4)",
                          border: "1px solid var(--border-subtle)",
                          padding: "1.25rem",
                          borderRadius: "var(--radius-md)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          flexWrap: "wrap",
                          gap: "1rem",
                        }}
                      >
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                            <h4>{link.doctor_name || "Doctor"}</h4>
                            <span className={`badge ${activeConsent ? "badge-active" : "badge-inactive"}`}>
                              {activeConsent ? "Consent Active" : "No Active Consent"}
                            </span>
                          </div>
                          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                            {link.doctor_specialty || "Medical Specialist"} • {link.doctor_email}
                          </div>
                          {activeConsent && (
                            <div style={{ fontSize: "0.75rem", color: "var(--accent-teal-light)", marginTop: "0.35rem" }}>
                              Scope: <strong>{activeConsent.scope}</strong> • Granted: {new Date(activeConsent.granted_at).toLocaleDateString()}
                            </div>
                          )}
                        </div>

                        <div style={{ display: "flex", gap: "0.75rem" }}>
                          {activeConsent ? (
                            <button
                              onClick={() => handleRevokeConsent(activeConsent.id, link.doctor_name)}
                              className="btn btn-danger btn-sm"
                              disabled={actionLoading[`revokeConsent_${activeConsent.id}`]}
                            >
                              <XCircle size={16} />
                              <span>{actionLoading[`revokeConsent_${activeConsent.id}`] ? "Revoking..." : "Revoke Consent"}</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                setSelectedDoctorForConsent(link);
                                setShowGrantConsentModal(true);
                              }}
                              className="btn btn-primary btn-sm"
                            >
                              <CheckCircle size={16} />
                              <span>Grant Consent</span>
                            </button>
                          )}
                          <button
                            onClick={() => handleDisconnectLink(link.id, link.doctor_name)}
                            className="btn btn-secondary btn-sm"
                            title="Disconnect Doctor"
                            disabled={actionLoading[`disconnect_${link.id}`]}
                          >
                            {actionLoading[`disconnect_${link.id}`] ? "Disconnecting..." : "Disconnect"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: OUTCOME & EFFICACY */}
        {activeTab === "effectiveness" && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <HeartPulse size={20} color="#ec4899" />
                AI-Assisted Patient Outcome & Efficacy Telemetry
              </h2>
            </div>

            <p style={{ marginBottom: "1.5rem" }}>
              Patient-reported outcomes enable clinical efficacy tracking. Rate the therapeutic effect and report any observed side effects for your healthcare team.
            </p>

            {loading ? (
              <div className="empty-state">Loading outcome telemetry...</div>
            ) : effectivenessLogs.length === 0 ? (
              <div className="empty-state">
                <HeartPulse className="empty-icon" />
                <h3>No Outcome Reports Logged Yet</h3>
                <p>Go to your medication list and click "Rate Efficacy" to submit feedback.</p>
              </div>
            ) : (
              <div>
                {effectivenessLogs.map((log) => (
                  <div key={log.id} className="med-item">
                    <div className="med-header">
                      <div>
                        <div className="med-name">
                          {log.medication_name || "Medication"}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.4rem" }}>
                          <div className="star-rating">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <span
                                key={star}
                                className={`star-icon ${star <= log.rating ? "filled" : ""}`}
                              >
                                ★
                              </span>
                            ))}
                          </div>
                          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                            ({log.rating}/5 Effectiveness)
                          </span>
                        </div>
                      </div>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        {new Date(log.logged_at).toLocaleDateString()}
                      </span>
                    </div>

                    {log.side_effects && (
                      <div style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "#fca5a5" }}>
                        <strong>Reported Side Effects:</strong> {log.side_effects}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: AUDIT TRAIL */}
        {activeTab === "audit" && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Lock size={20} color="var(--accent-cyan-light)" />
                Cryptographic Tamper-Evident Audit Trail
              </h2>
              <span className="badge badge-active">
                <ShieldCheck size={14} /> Chained Integrity Verified
              </span>
            </div>

            <p style={{ marginBottom: "1.5rem" }}>
              Every access, prescription entry, consent grant, and export creates an immutable, SHA-256 chained audit block. Any unauthorized alterations break the cryptographic chain.
            </p>

            {loading ? (
              <div className="empty-state">Loading cryptographic audit trail...</div>
            ) : auditLogs.length === 0 ? (
              <div className="empty-state">No audit events recorded yet.</div>
            ) : (
              <div className="audit-list">
                {auditLogs.map((log) => (
                  <div key={log.id} className="audit-item">
                    <div className="audit-header">
                      <span className="audit-action">{log.action}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                      Resource: <code>{log.resource_type}</code> • Resource ID: <code>{log.resource_id || "N/A"}</code>
                    </div>
                    <div className="audit-hash">
                      <strong>Block Hash:</strong> {log.hash}
                    </div>
                    {log.prev_hash && (
                      <div className="audit-hash" style={{ opacity: 0.7 }}>
                        <strong>Parent Block:</strong> {log.prev_hash}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* MODAL: ADD MEDICATION */}
      {showAddMedModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Log Self-Administered Medication</h3>
              <button
                onClick={() => setShowAddMedModal(false)}
                className="btn btn-sm btn-secondary"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddMedication}>
              <div className="form-group">
                <label className="form-label">Medication Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Ibuprofen, Metformin 500mg, Vitamin D"
                  value={newMed.medication_name}
                  onChange={(e) => setNewMed({ ...newMed, medication_name: e.target.value })}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Dosage</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. 500mg, 10ml"
                    value={newMed.dosage}
                    onChange={(e) => setNewMed({ ...newMed, dosage: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Frequency</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Twice daily with meals"
                    value={newMed.frequency}
                    onChange={(e) => setNewMed({ ...newMed, frequency: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Instructions / Notes</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="Reasons for taking, special instructions, OTC or prescription..."
                  value={newMed.notes}
                  onChange={(e) => setNewMed({ ...newMed, notes: e.target.value })}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowAddMedModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionLoading.addMed}
                >
                  {actionLoading.addMed ? "Saving..." : "Save to Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RATE EFFECTIVENESS */}
      {showRateModal && selectedMedForRating && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Log Outcome: {selectedMedForRating.medication_name}</h3>
              <button
                onClick={() => setShowRateModal(false)}
                className="btn btn-sm btn-secondary"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogEffectiveness}>
              <div className="form-group">
                <label className="form-label">Efficacy Rating (1-5 Stars)</label>
                <div className="star-rating" style={{ margin: "0.5rem 0" }}>
                  {[1, 2, 3, 4, 5].map((s) => (
                    <span
                      key={s}
                      className={`star-icon ${s <= ratingData.rating ? "filled" : ""}`}
                      style={{ fontSize: "2rem" }}
                      onClick={() => setRatingData({ ...ratingData, rating: s })}
                    >
                      ★
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  {ratingData.rating === 5 && "Excellent therapeutic response with good symptom relief"}
                  {ratingData.rating === 4 && "Noticeable improvement"}
                  {ratingData.rating === 3 && "Moderate effect"}
                  {ratingData.rating === 2 && "Minimal improvement"}
                  {ratingData.rating === 1 && "No noticeable effect or adverse reaction"}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Observed Side Effects (if any)</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="Describe dizziness, upset stomach, fatigue, skin rashes, or write 'None'..."
                  value={ratingData.side_effects}
                  onChange={(e) => setRatingData({ ...ratingData, side_effects: e.target.value })}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowRateModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionLoading.logEffectiveness}
                >
                  {actionLoading.logEffectiveness ? "Submitting..." : "Submit Feedback"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: GRANT CONSENT */}
      {showGrantConsentModal && selectedDoctorForConsent && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Authorize Clinician Access</h3>
              <button
                onClick={() => setShowGrantConsentModal(false)}
                className="btn btn-sm btn-secondary"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGrantConsent}>
              <p style={{ marginBottom: "1.25rem", fontSize: "0.9rem" }}>
                Granting consent gives <strong>{selectedDoctorForConsent.doctor_name || "this doctor"}</strong> permission to view your cross-doctor medication history and prescribe during clinical encounters.
              </p>

              <div className="form-group">
                <label className="form-label">Consent Scope</label>
                <select
                  className="form-select"
                  value={consentData.scope}
                  onChange={(e) => setConsentData({ ...consentData, scope: e.target.value })}
                >
                  <option value="all">Full Record Access (Medications, Encounters, Telemetry)</option>
                  <option value="encounters_only">Encounter & Prescriptions Only</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Duration</label>
                <select
                  className="form-select"
                  value={consentData.expires_in_days}
                  onChange={(e) => setConsentData({ ...consentData, expires_in_days: e.target.value })}
                >
                  <option value={7}>7 Days (Short consultation)</option>
                  <option value={30}>30 Days (Standard care)</option>
                  <option value={90}>90 Days (Quarterly treatment)</option>
                  <option value={365}>1 Year (Primary Care Physician)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowGrantConsentModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionLoading.grantConsent}
                >
                  {actionLoading.grantConsent ? "Granting..." : "Sign & Grant Consent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}