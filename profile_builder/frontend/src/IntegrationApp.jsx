import React, { useState } from "react";

/**
 * RADIX Talent Match — Unified 5-Step Single Page Integration Flow
 */
export default function IntegrationApp() {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1: JD Analytics state
  const [jdFile, setJdFile] = useState(null);
  const [jdData, setJdData] = useState(null);

  // Step 2: Resume Parsing state
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeData, setResumeData] = useState(null);

  // Step 3: Profile Builder state
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    education: "",
    skills: [],
    hackathons: [],
    internships: [],
    certifications: [],
    preferred_roles: [],
    cv_file: "",
  });
  const [savedProfileId, setSavedProfileId] = useState("");

  // Step 4: Talent Check state
  const [selectedCompany, setSelectedCompany] = useState("Google");
  const [talentCheckResult, setTalentCheckResult] = useState(null);

  // Step 5: Skill Match state
  const [skillMatchResult, setSkillMatchResult] = useState(null);

  const API_BASE = "";

  // Step 1 Handler: Process JD
  const handleJdUpload = async () => {
    if (!jdFile) return setError("Please select a JD file.");
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", jdFile);
      const res = await fetch(`${API_BASE}/flow/jd`, { method: "POST", body: formData });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Server returned ${res.status}`);
      }
      const data = await res.json();
      setJdData(data);
      setCurrentStep(2);
    } catch (err) {
      setError(`JD Analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Step 2 Handler: Process Resume
  const handleResumeUpload = async () => {
    if (!resumeFile) return setError("Please select a Resume file.");
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", resumeFile);
      const res = await fetch(`${API_BASE}/flow/resume`, { method: "POST", body: formData });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Server returned ${res.status}`);
      }
      const data = await res.json();
      setResumeData(data);

      // Pre-fill profile builder state from extracted resume data
      const extractedFields = data.fields || {};
      const extractedSkills = data.skills?.skills || data.skills || [];

      setProfile({
        name: extractedFields.name || "Candidate Name",
        email: extractedFields.email || "candidate@example.com",
        education: extractedFields.education || "",
        skills: Array.isArray(extractedSkills) ? extractedSkills : [],
        hackathons: [],
        internships: extractedFields.internships || [],
        certifications: extractedFields.certifications || [],
        preferred_roles: [],
        cv_file: data.source_file || resumeFile.name,
      });

      setCurrentStep(3);
    } catch (err) {
      setError(`Resume Parsing failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Step 3 Handler: Save Profile
  const handleSaveProfile = async () => {
    if (!profile.name || !profile.email) return setError("Name and Email are required.");
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setSavedProfileId(data.profile_id);
      setCurrentStep(4);
    } catch (err) {
      setError(`Save Profile failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Step 4 Handler: Talent Check
  const handleTalentCheck = async () => {
    if (!savedProfileId) return setError("Please save your profile first.");
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/talent-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: savedProfileId, company: selectedCompany }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setTalentCheckResult(data);
      setCurrentStep(5);
    } catch (err) {
      setError(`Talent Check failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Step 5 Handler: Skill Match
  const handleSkillMatch = async () => {
    if (!savedProfileId || !jdData) return setError("Missing profile or JD data.");
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/flow/skill-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: savedProfileId, jd_analytics: jdData }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setSkillMatchResult(data);
    } catch (err) {
      setError(`Skill Match failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1>RADIX Talent Match — Unified Demo</h1>
      <p>5-Step End-to-End Recruitment & Skill Matching Workflow</p>

      {/* Step Indicators */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {[1, 2, 3, 4, 5].map((s) => (
          <button
            key={s}
            onClick={() => setCurrentStep(s)}
            style={{
              flex: 1,
              padding: 10,
              fontWeight: "bold",
              backgroundColor: currentStep === s ? "#0066cc" : "#e0e0e0",
              color: currentStep === s ? "#fff" : "#333",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Step {s}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ padding: 12, backgroundColor: "#ffdddd", color: "#cc0000", borderRadius: 4, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Step 1: Upload JD */}
      {currentStep === 1 && (
        <div style={{ border: "1px solid #ccc", padding: 20, borderRadius: 8 }}>
          <h2>Step 1: Upload Job Description</h2>
          <input type="file" onChange={(e) => setJdFile(e.target.files[0])} />
          <br /><br />
          <button onClick={handleJdUpload} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Analyzing JD..." : "Analyze JD & Next"}
          </button>
          {jdData && (
            <pre style={{ background: "#f5f5f5", padding: 12, marginTop: 16, overflowX: "auto" }}>
              {JSON.stringify(jdData, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Step 2: Upload Resume */}
      {currentStep === 2 && (
        <div style={{ border: "1px solid #ccc", padding: 20, borderRadius: 8 }}>
          <h2>Step 2: Upload Candidate Resume</h2>
          <input type="file" onChange={(e) => setResumeFile(e.target.files[0])} />
          <br /><br />
          <button onClick={handleResumeUpload} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Parsing Resume..." : "Parse Resume & Pre-fill Profile"}
          </button>
          {resumeData && (
            <pre style={{ background: "#f5f5f5", padding: 12, marginTop: 16, overflowX: "auto" }}>
              {JSON.stringify(resumeData, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Step 3: Build/Edit Profile */}
      {currentStep === 3 && (
        <div style={{ border: "1px solid #ccc", padding: 20, borderRadius: 8 }}>
          <h2>Step 3: Candidate Profile (Pre-filled from Resume)</h2>
          <label>Name:</label><br />
          <input
            type="text"
            value={profile.name}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            style={{ width: "100%", padding: 8, marginBottom: 12 }}
          />
          <label>Email:</label><br />
          <input
            type="email"
            value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            style={{ width: "100%", padding: 8, marginBottom: 12 }}
          />
          <label>Education:</label><br />
          <input
            type="text"
            value={profile.education}
            onChange={(e) => setProfile({ ...profile, education: e.target.value })}
            style={{ width: "100%", padding: 8, marginBottom: 12 }}
          />
          <h4>Extracted Skills ({profile.skills.length})</h4>
          <ul>
            {profile.skills.map((s, idx) => (
              <li key={idx}>[{s.category_code}] {s.skill_name} (Confidence: {s.confidence})</li>
            ))}
          </ul>
          <button onClick={handleSaveProfile} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Saving Profile..." : "Save Profile & Proceed to Talent Check"}
          </button>
        </div>
      )}

      {/* Step 4: Talent Check */}
      {currentStep === 4 && (
        <div style={{ border: "1px solid #ccc", padding: 20, borderRadius: 8 }}>
          <h2>Step 4: Talent Check Benchmark</h2>
          <label>Select Target Company:</label><br />
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            style={{ padding: 8, marginBottom: 16 }}
          >
            <option value="Google">Google</option>
            <option value="Microsoft">Microsoft</option>
            <option value="Oracle Financial Services Software">Oracle Financial Services</option>
          </select>
          <br />
          <button onClick={handleTalentCheck} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Calculating..." : "Run Talent Check & Next"}
          </button>
          {talentCheckResult && (
            <div>
              <h3>Readiness Score: {talentCheckResult.readiness_score}%</h3>
              <pre style={{ background: "#f5f5f5", padding: 12, overflowX: "auto" }}>
                {JSON.stringify(talentCheckResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Step 5: Skill Match */}
      {currentStep === 5 && (
        <div style={{ border: "1px solid #ccc", padding: 20, borderRadius: 8 }}>
          <h2>Step 5: Skill Match Against Job Description</h2>
          <button onClick={handleSkillMatch} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Matching..." : "Execute Skill Match"}
          </button>
          {skillMatchResult && (
            <div>
              <h3>Match Score: {skillMatchResult.match_score}%</h3>
              <p><strong>Summary:</strong> {skillMatchResult.summary}</p>
              <h4>Matched Skills ({skillMatchResult.matched_skills.length}):</h4>
              <ul>
                {skillMatchResult.matched_skills.map((m, i) => (
                  <li key={i}>[{m.category_code}] {m.jd_skill_name} — {m.explanation}</li>
                ))}
              </ul>
              <h4>Missing Skills ({skillMatchResult.missing_skills.length}):</h4>
              <ul>
                {skillMatchResult.missing_skills.map((m, i) => (
                  <li key={i}>[{m.category_code}] {m.jd_skill_name} ({m.importance}) — {m.explanation}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
