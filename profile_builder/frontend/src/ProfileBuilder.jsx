import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";
const CATEGORY_CODES = [
  "DSA", "COD", "OOD", "APTI", "COMM", "AI",
  "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER"
];

function emptySkill() {
  return { skill_name: "", category_code: "", evidence: "", confidence: null };
}

function emptyProfile() {
  return {
    name: "",
    email: "",
    education: "",
    skills: [emptySkill()],
    hackathons: [],
    internships: [],
    certifications: [],
    preferred_roles: [],
    cv_file: ""
  };
}

// Simple comma-separated list input for hackathons/internships/certifications/preferred_roles
function ListField({ label, values, onChange }) {
  const [text, setText] = useState(values.join(", "));

  useEffect(() => {
    setText(values.join(", "));
  }, [values]);

  const commit = () => {
    const parsed = text.split(",").map(s => s.trim()).filter(Boolean);
    onChange(parsed);
  };

  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>{label}</label>
      <input
        style={{ width: "100%", padding: 8, border: "1px solid #ccc", borderRadius: 4 }}
        value={text}
        placeholder="Comma-separated"
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
      />
    </div>
  );
}

export default function ProfileBuilder() {
  const [profile, setProfile] = useState(emptyProfile());
  const [profileId, setProfileId] = useState("");
  const [savedProfiles, setSavedProfiles] = useState([]);
  const [errors, setErrors] = useState([]);
  const [status, setStatus] = useState("");

  const refreshList = () => {
    fetch(`${API_BASE}/profile`)
      .then(r => r.json())
      .then(setSavedProfiles)
      .catch(() => {});
  };

  useEffect(() => { refreshList(); }, []);

  const loadProfile = (id) => {
    fetch(`${API_BASE}/profile/${id}`)
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setProfileId(id);
        setStatus(`Loaded ${id}`);
      });
  };

  const updateField = (field, value) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  const updateSkill = (index, field, value) => {
    const skills = [...profile.skills];
    skills[index] = { ...skills[index], [field]: value };
    setProfile(prev => ({ ...prev, skills }));
  };

  const addSkill = () => {
    setProfile(prev => ({ ...prev, skills: [...prev.skills, emptySkill()] }));
  };

  const removeSkill = (index) => {
    setProfile(prev => ({ ...prev, skills: prev.skills.filter((_, i) => i !== index) }));
  };

  const saveProfile = async () => {
    setStatus("Saving...");
    setErrors([]);
    try {
      const res = await fetch(`${API_BASE}/profile/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...profile, profile_id: profileId || undefined })
      });
      const data = await res.json();
      if (!res.ok) {
        setErrors(data.detail?.errors || ["Save failed"]);
        setStatus("");
        return;
      }
      setProfileId(data.profile_id);
      setStatus(`Saved as ${data.profile_id}`);
      refreshList();
    } catch (err) {
      setStatus("");
      setErrors(["Could not reach backend — is it running on :8000?"]);
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <h2>RADIX Profile Builder</h2>

      {savedProfiles.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontWeight: 600 }}>Load existing profile: </label>
          <select onChange={(e) => e.target.value && loadProfile(e.target.value)} defaultValue="">
            <option value="">-- select --</option>
            {savedProfiles.map(p => (
              <option key={p.profile_id} value={p.profile_id}>{p.name} ({p.profile_id})</option>
            ))}
          </select>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Name</label>
        <input
          style={{ width: "100%", padding: 8, border: "1px solid #ccc", borderRadius: 4 }}
          value={profile.name}
          onChange={(e) => updateField("name", e.target.value)}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Email</label>
        <input
          style={{ width: "100%", padding: 8, border: "1px solid #ccc", borderRadius: 4 }}
          value={profile.email}
          onChange={(e) => updateField("email", e.target.value)}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>Education</label>
        <input
          style={{ width: "100%", padding: 8, border: "1px solid #ccc", borderRadius: 4 }}
          value={profile.education}
          onChange={(e) => updateField("education", e.target.value)}
        />
      </div>

      <h3>Skills</h3>
      {profile.skills.map((skill, i) => (
        <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
          <input
            placeholder="Skill name"
            style={{ flex: 2, padding: 6, border: "1px solid #ccc", borderRadius: 4 }}
            value={skill.skill_name}
            onChange={(e) => updateSkill(i, "skill_name", e.target.value)}
          />
          <select
            style={{ flex: 1, padding: 6 }}
            value={skill.category_code}
            onChange={(e) => updateSkill(i, "category_code", e.target.value)}
          >
            <option value="">Select</option>
            {CATEGORY_CODES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <span
            title="Confidence score (read-only)"
            style={{
              flex: 1,
              padding: "6px",
              background: "#f3f4f6",
              border: "1px solid #ccc",
              borderRadius: 4,
              fontSize: "0.9em",
              color: "#4b5563",
              textAlign: "center",
              userSelect: "none"
            }}
          >
            {skill.confidence != null ? skill.confidence : "nil"}
          </span>
          <input
            placeholder="Evidence"
            style={{ flex: 2, padding: 6, border: "1px solid #ccc", borderRadius: 4 }}
            value={skill.evidence}
            onChange={(e) => updateSkill(i, "evidence", e.target.value)}
          />
          <button onClick={() => removeSkill(i)} style={{ padding: "6px 10px" }}>✕</button>
        </div>
      ))}
      <button onClick={addSkill} style={{ marginBottom: 16, padding: "6px 12px" }}>+ Add skill</button>

      <ListField label="Hackathons" values={profile.hackathons} onChange={(v) => updateField("hackathons", v)} />
      <ListField label="Internships" values={profile.internships} onChange={(v) => updateField("internships", v)} />
      <ListField label="Certifications" values={profile.certifications} onChange={(v) => updateField("certifications", v)} />
      <ListField label="Preferred Roles" values={profile.preferred_roles} onChange={(v) => updateField("preferred_roles", v)} />

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>CV File name</label>
        <input
          style={{ width: "100%", padding: 8, border: "1px solid #ccc", borderRadius: 4 }}
          value={profile.cv_file}
          onChange={(e) => updateField("cv_file", e.target.value)}
          placeholder="e.g. resume.pdf"
        />
      </div>

      {errors.length > 0 && (
        <div style={{ background: "#fee", padding: 12, borderRadius: 4, marginBottom: 12 }}>
          {errors.map((e, i) => <div key={i} style={{ color: "#a00" }}>• {e}</div>)}
        </div>
      )}

      <button
        onClick={saveProfile}
        style={{ padding: "10px 20px", background: "#1a3a5c", color: "white", border: "none", borderRadius: 4, fontWeight: 600 }}
      >
        Save Profile
      </button>
      {status && <span style={{ marginLeft: 12, color: "#080" }}>{status}</span>}
    </div>
  );
}
