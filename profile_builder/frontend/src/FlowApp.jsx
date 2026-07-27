import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "./components/Logo";
import ProgressBar from "./components/ProgressBar";
import RadialScore from "./components/RadialScore";
import SkillGroup from "./components/SkillGroup";

const CATEGORY_LABELS = {
  DSA: "DSA", COD: "Coding", OOD: "OOD", APTI: "Aptitude",
  COMM: "Communication", AI: "AI/ML", CLOUD: "Cloud", SQL: "SQL/DB",
  SWE: "SWE", SYSD: "System Design", NETW: "Networking", OS: "OS", OTHER: "Other",
};

const pageVariants = {
  initial: { opacity: 0, x: 40 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -40 },
};

export default function FlowApp() {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [completedSteps, setCompletedSteps] = useState([]);

  // Step 1
  const [jdFile, setJdFile] = useState(null);
  const [jdData, setJdData] = useState(null);

  // Step 2
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeData, setResumeData] = useState(null);

  // Step 3
  const [profile, setProfile] = useState({
    name: "", email: "", education: "",
    skills: [], hackathons: [], internships: [],
    certifications: [], preferred_roles: [], cv_file: "",
  });
  const [savedProfileId, setSavedProfileId] = useState("");
  const [profileSaved, setProfileSaved] = useState(false);
  const [glowFields, setGlowFields] = useState(false);

  // Step 4
  const [selectedCompany, setSelectedCompany] = useState("Google");
  const [talentCheckResult, setTalentCheckResult] = useState(null);

  // Step 5
  const [skillMatchResult, setSkillMatchResult] = useState(null);

  const API_BASE = "";

  const markComplete = (step) => {
    setCompletedSteps((prev) => (prev.includes(step) ? prev : [...prev, step]));
  };

  // ── Step 1 ──
  const handleJdUpload = async () => {
    if (!jdFile) return setError("Please select a JD file.");
    setLoading(true); setError("");
    try {
      const formData = new FormData();
      formData.append("file", jdFile);
      const res = await fetch(`${API_BASE}/flow/jd`, { method: "POST", body: formData });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server ${res.status}`); }
      const data = await res.json();
      setJdData(data);
      markComplete(1);
      setCurrentStep(2);
    } catch (err) { setError(`JD Analysis failed: ${err.message}`); }
    finally { setLoading(false); }
  };

  // ── Step 2 ──
  const handleResumeUpload = async () => {
    if (!resumeFile) return setError("Please select a Resume file.");
    setLoading(true); setError("");
    try {
      const formData = new FormData();
      formData.append("file", resumeFile);
      const res = await fetch(`${API_BASE}/flow/resume`, { method: "POST", body: formData });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server ${res.status}`); }
      const data = await res.json();
      setResumeData(data);
      const f = data.fields || {};
      const sk = data.skills?.skills || data.skills || [];
      setProfile({
        name: f.name || "Candidate Name",
        email: f.email || "candidate@example.com",
        education: f.education || "",
        skills: Array.isArray(sk) ? sk : [],
        hackathons: [],
        internships: f.internships || [],
        certifications: f.certifications || [],
        preferred_roles: [],
        cv_file: data.source_file || resumeFile.name,
      });
      markComplete(2);
      setCurrentStep(3);
      setGlowFields(true);
      setTimeout(() => setGlowFields(false), 1500);
    } catch (err) { setError(`Resume Parsing failed: ${err.message}`); }
    finally { setLoading(false); }
  };

  // ── Step 3 ──
  const handleSaveProfile = async () => {
    if (!profile.name || !profile.email) return setError("Name and Email required.");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server ${res.status}`); }
      const data = await res.json();
      setSavedProfileId(data.profile_id);
      setProfileSaved(true);
      markComplete(3);
      setTimeout(() => setCurrentStep(4), 800);
    } catch (err) { setError(`Save Profile failed: ${err.message}`); }
    finally { setLoading(false); }
  };

  // ── Step 4 ──
  const handleTalentCheck = async () => {
    if (!savedProfileId) return setError("Save a profile first.");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/talent-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: savedProfileId, company: selectedCompany }),
      });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server ${res.status}`); }
      const data = await res.json();
      setTalentCheckResult(data);
      markComplete(4);
    } catch (err) { setError(`Talent Check failed: ${err.message}`); }
    finally { setLoading(false); }
  };

  // ── Step 5 ──
  const handleSkillMatch = async () => {
    if (!savedProfileId || !jdData) return setError("Missing profile or JD data.");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/skill-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: savedProfileId, jd_analytics: jdData }),
      });
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Server ${res.status}`); }
      const data = await res.json();
      setSkillMatchResult(data);
      markComplete(5);
    } catch (err) { setError(`Skill Match failed: ${err.message}`); }
    finally { setLoading(false); }
  };

  // ── Shared UI Helpers ──
  const ActionButton = ({ onClick, disabled, loadingText, text, className = "" }) => (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`liquid-glass rounded-full px-8 py-3 text-sm font-medium cursor-pointer transition-all hover:scale-[1.03] disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
      style={{ color: "var(--foreground)" }}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <motion.span
            className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
          />
          {loadingText}
        </span>
      ) : text}
    </button>
  );

  const StepCard = ({ children, title }) => (
    <div className="w-full max-w-3xl mx-auto">
      <h2
        className="text-2xl font-semibold mb-6"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      {children}
    </div>
  );

  return (
    <div className="min-h-dvh flex flex-col" style={{ background: "var(--background)" }}>
      {/* ── Nav ── */}
      <nav className="liquid-glass flex items-center justify-between px-8 py-4 sticky top-0 z-50">
        <Link to="/" style={{ textDecoration: "none" }}>
          <Logo />
        </Link>
      </nav>

      {/* ── Progress Bar ── */}
      <ProgressBar currentStep={currentStep} completedSteps={completedSteps} />

      {/* ── Error Banner ── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="max-w-3xl mx-auto w-full mb-4 px-4"
          >
            <div
              className="rounded-lg px-4 py-3 text-sm flex items-center gap-2"
              style={{ background: "hsla(0,72%,51%,0.15)", color: "var(--danger)", border: "1px solid hsla(0,72%,51%,0.3)" }}
            >
              <span>&#x26A0;</span> {error}
              <button onClick={() => setError("")} className="ml-auto text-xs opacity-60 hover:opacity-100 cursor-pointer" style={{ background: "none", border: "none", color: "inherit" }}>dismiss</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Step Content ── */}
      <main className="flex-1 px-4 pb-16">
        <AnimatePresence mode="wait">
          {/* ════════ STEP 1 ════════ */}
          {currentStep === 1 && (
            <motion.div key="step1" variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.35 }}>
              <StepCard title="Upload Job Description">
                <p className="text-sm mb-6" style={{ color: "var(--muted-foreground)" }}>
                  Upload a JD file (PDF, DOCX, or TXT) and we'll extract the required skills.
                </p>
                <div className="rounded-xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <label className="flex flex-col items-center justify-center py-10 border-2 border-dashed rounded-lg cursor-pointer transition-colors hover:border-[var(--primary)]" style={{ borderColor: "var(--border)" }}>
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--muted-foreground)" strokeWidth="1.5" className="mb-3">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                      {jdFile ? jdFile.name : "Click to select a JD file"}
                    </span>
                    <input type="file" className="hidden" onChange={(e) => setJdFile(e.target.files[0])} accept=".pdf,.docx,.txt,.doc" />
                  </label>
                  <div className="mt-6 flex justify-end">
                    <ActionButton onClick={handleJdUpload} loadingText="Analyzing..." text="Analyze JD & Continue" />
                  </div>
                </div>
                {jdData && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8">
                    <h3 className="text-lg font-semibold mb-1" style={{ fontFamily: "var(--font-display)" }}>
                      {jdData.company} — {jdData.role}
                    </h3>
                    <p className="text-xs mb-4" style={{ color: "var(--muted-foreground)" }}>
                      {jdData.skills?.length || 0} skills extracted from {jdData.source_file}
                    </p>
                    <SkillGroup skills={jdData.skills || []} />
                  </motion.div>
                )}
              </StepCard>
            </motion.div>
          )}

          {/* ════════ STEP 2 ════════ */}
          {currentStep === 2 && (
            <motion.div key="step2" variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.35 }}>
              <StepCard title="Upload Candidate Resume">
                <p className="text-sm mb-6" style={{ color: "var(--muted-foreground)" }}>
                  Upload a resume (PDF or DOCX) to extract skills and biographical fields.
                </p>
                <div className="rounded-xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <label className="flex flex-col items-center justify-center py-10 border-2 border-dashed rounded-lg cursor-pointer transition-colors hover:border-[var(--primary)]" style={{ borderColor: "var(--border)" }}>
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--muted-foreground)" strokeWidth="1.5" className="mb-3">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" strokeLinecap="round" strokeLinejoin="round" />
                      <polyline points="14,2 14,8 20,8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                      {resumeFile ? resumeFile.name : "Click to select a resume file"}
                    </span>
                    <input type="file" className="hidden" onChange={(e) => setResumeFile(e.target.files[0])} accept=".pdf,.docx,.doc" />
                  </label>
                  <div className="mt-6 flex justify-end">
                    <ActionButton onClick={handleResumeUpload} loadingText="Parsing..." text="Parse Resume & Pre-fill Profile" />
                  </div>
                </div>
                {resumeData && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8">
                    <p className="text-xs mb-4" style={{ color: "var(--muted-foreground)" }}>
                      {resumeData.skills?.length || 0} skills extracted
                    </p>
                    <SkillGroup skills={resumeData.skills || []} />
                    {resumeData.fields && (
                      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="mt-6 rounded-xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                        <h4 className="text-sm font-semibold mb-3" style={{ fontFamily: "var(--font-display)" }}>Structured Fields</h4>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          {resumeData.fields.education && <div><span style={{ color: "var(--muted-foreground)" }}>Education:</span> {resumeData.fields.education}</div>}
                          {resumeData.fields.internships?.length > 0 && <div><span style={{ color: "var(--muted-foreground)" }}>Internships:</span> {resumeData.fields.internships.join(", ")}</div>}
                          {resumeData.fields.certifications?.length > 0 && <div><span style={{ color: "var(--muted-foreground)" }}>Certifications:</span> {resumeData.fields.certifications.join(", ")}</div>}
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </StepCard>
            </motion.div>
          )}

          {/* ════════ STEP 3 ════════ */}
          {currentStep === 3 && (
            <motion.div key="step3" variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.35 }}>
              <StepCard title="Candidate Profile">
                <p className="text-sm mb-6" style={{ color: "var(--muted-foreground)" }}>
                  Review and edit the pre-filled profile before saving.
                </p>
                <div className="rounded-xl p-6 space-y-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <div>
                    <label className="text-xs font-medium mb-1 block" style={{ color: "var(--muted-foreground)" }}>Full Name</label>
                    <input type="text" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} className={glowFields ? "glow-highlight" : ""} />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1 block" style={{ color: "var(--muted-foreground)" }}>Email</label>
                    <input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} className={glowFields ? "glow-highlight" : ""} />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1 block" style={{ color: "var(--muted-foreground)" }}>Education</label>
                    <input type="text" value={profile.education} onChange={(e) => setProfile({ ...profile, education: e.target.value })} className={glowFields ? "glow-highlight" : ""} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold mt-4 mb-2" style={{ fontFamily: "var(--font-display)" }}>
                      Extracted Skills ({profile.skills.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {profile.skills.map((s, i) => (
                        <motion.span
                          key={i}
                          className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium"
                          style={{ background: "var(--secondary)", border: "1px solid var(--border)" }}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: i * 0.03 }}
                        >
                          <span style={{ color: "var(--primary)" }}>{s.category_code}</span>
                          <span>{s.skill_name}</span>
                        </motion.span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-4 pt-4">
                    {profileSaved && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.5 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1 text-sm"
                        style={{ color: "var(--success)" }}
                      >
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="3,8 7,12 13,4" /></svg>
                        Saved as {savedProfileId}
                      </motion.span>
                    )}
                    <ActionButton onClick={handleSaveProfile} loadingText="Saving..." text="Save Profile & Continue" />
                  </div>
                </div>
              </StepCard>
            </motion.div>
          )}

          {/* ════════ STEP 4 ════════ */}
          {currentStep === 4 && (
            <motion.div key="step4" variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.35 }}>
              <StepCard title="Talent Check">
                <p className="text-sm mb-6" style={{ color: "var(--muted-foreground)" }}>
                  Benchmark your profile against a company's skill requirements.
                </p>
                <div className="rounded-xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <div className="flex items-end gap-4 mb-6">
                    <div className="flex-1">
                      <label className="text-xs font-medium mb-1 block" style={{ color: "var(--muted-foreground)" }}>Target Company</label>
                      <select value={selectedCompany} onChange={(e) => setSelectedCompany(e.target.value)}>
                        <option value="Google">Google</option>
                        <option value="Microsoft">Microsoft</option>
                        <option value="Oracle Financial Services Software">Oracle Financial Services</option>
                      </select>
                    </div>
                    <ActionButton
                      onClick={handleTalentCheck}
                      disabled={!savedProfileId}
                      loadingText="Analyzing..."
                      text={savedProfileId ? "Run Talent Check" : "Save a profile first"}
                    />
                  </div>
                </div>

                {talentCheckResult && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 space-y-8">
                    <div className="flex justify-center">
                      <RadialScore value={talentCheckResult.readiness_score} label="Readiness" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold mb-4" style={{ fontFamily: "var(--font-display)" }}>Skillset Gap Breakdown</h4>
                      <div className="space-y-3">
                        {talentCheckResult.skillset_gap?.map((item, i) => (
                          <motion.div
                            key={item.category_code}
                            initial={{ opacity: 0, x: -16 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.06 }}
                            className="rounded-lg px-4 py-3"
                            style={{ background: "var(--card)", border: `1px solid ${item.gap ? "hsla(75,40%,50%,0.4)" : "var(--border)"}` }}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium flex items-center gap-2">
                                {item.gap && <span className="w-2 h-2 rounded-full" style={{ background: "var(--primary)" }} />}
                                {CATEGORY_LABELS[item.category_code] || item.category_code}
                              </span>
                              <span className="text-xs" style={{ color: item.gap ? "var(--primary)" : "var(--success)" }}>
                                {item.candidate_level}/{item.required_level}
                              </span>
                            </div>
                            <div className="flex gap-1 items-center">
                              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                                <motion.div
                                  className="h-full rounded-full"
                                  style={{ background: item.gap ? "var(--primary)" : "var(--success)" }}
                                  initial={{ width: 0 }}
                                  animate={{ width: `${(item.candidate_level / 10) * 100}%` }}
                                  transition={{ delay: i * 0.06, duration: 0.6 }}
                                />
                              </div>
                              <div className="w-1 h-4 rounded" style={{ background: "var(--muted-foreground)", marginLeft: `calc(${(item.required_level / 10) * 100}% - 2px)`, position: "relative", left: `-${(item.required_level / 10) * 100}%` }} />
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-end">
                      <ActionButton onClick={() => setCurrentStep(5)} text="Continue to Skill Match" />
                    </div>
                  </motion.div>
                )}
              </StepCard>
            </motion.div>
          )}

          {/* ════════ STEP 5 ════════ */}
          {currentStep === 5 && (
            <motion.div key="step5" variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.35 }}>
              <StepCard title="Skill Match">
                <p className="text-sm mb-6" style={{ color: "var(--muted-foreground)" }}>
                  Matching profile <strong>{savedProfileId}</strong> against JD: <strong>{jdData?.source_file}</strong>
                </p>
                <div className="rounded-xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <ActionButton onClick={handleSkillMatch} loadingText="Matching..." text="Run Skill Match" />
                </div>

                {skillMatchResult && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 space-y-8">
                    <div className="flex justify-center">
                      <RadialScore value={skillMatchResult.match_score} label="Match Score" />
                    </div>
                    {skillMatchResult.summary && (
                      <p className="text-sm text-center max-w-2xl mx-auto leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                        {skillMatchResult.summary}
                      </p>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Matched */}
                      <div>
                        <h4 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ fontFamily: "var(--font-display)", color: "var(--success)" }}>
                          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="3,8 7,12 13,4" /></svg>
                          Matched Skills ({skillMatchResult.matched_skills?.length || 0})
                        </h4>
                        <div className="space-y-2">
                          {skillMatchResult.matched_skills?.map((m, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: i * 0.06 }}
                              className="rounded-lg px-4 py-3"
                              style={{ background: "var(--card)", border: "1px solid var(--border)" }}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-semibold rounded px-1.5 py-0.5" style={{ background: "var(--secondary)", color: "var(--primary)" }}>{m.category_code}</span>
                                <span className="text-sm font-medium">{m.jd_skill_name}</span>
                              </div>
                              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{m.explanation}</p>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                      {/* Missing */}
                      <div>
                        <h4 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ fontFamily: "var(--font-display)", color: "var(--danger)" }}>
                          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="4" y1="4" x2="12" y2="12" /><line x1="12" y1="4" x2="4" y2="12" /></svg>
                          Missing Skills ({skillMatchResult.missing_skills?.length || 0})
                        </h4>
                        <div className="space-y-2">
                          {skillMatchResult.missing_skills?.map((m, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: i * 0.06 + 0.3 }}
                              className="rounded-lg px-4 py-3"
                              style={{ background: "hsla(0,72%,51%,0.06)", border: "1px solid hsla(0,72%,51%,0.2)" }}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-semibold rounded px-1.5 py-0.5" style={{ background: "hsla(0,72%,51%,0.15)", color: "var(--danger)" }}>{m.category_code}</span>
                                <span className="text-sm font-medium">{m.jd_skill_name}</span>
                                {m.importance && <span className="text-xs ml-auto" style={{ color: "var(--primary)" }}>{m.importance}</span>}
                              </div>
                              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{m.explanation}</p>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </StepCard>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
