import React from "react";
import { motion } from "framer-motion";

const CATEGORY_LABELS = {
  DSA: "Data Structures & Algorithms",
  COD: "Coding",
  OOD: "Object-Oriented Design",
  APTI: "Aptitude",
  COMM: "Communication",
  AI: "AI / Machine Learning",
  CLOUD: "Cloud / DevOps",
  SQL: "SQL / Databases",
  SWE: "Software Engineering",
  SYSD: "System Design",
  NETW: "Networking",
  OS: "Operating Systems",
  OTHER: "Other",
};

/**
 * Groups a skills array by category_code and renders them with staggered fade-in.
 * Confidence is rendered as a filled progress bar (0-100 int).
 */
export default function SkillGroup({ skills = [] }) {
  // Group by category_code
  const grouped = {};
  skills.forEach((s) => {
    const code = s.category_code || "OTHER";
    if (!grouped[code]) grouped[code] = [];
    grouped[code].push(s);
  });

  const categories = Object.keys(grouped);

  return (
    <div className="space-y-6">
      {categories.map((code, catIdx) => (
        <motion.div
          key={code}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: catIdx * 0.08, duration: 0.4 }}
        >
          <h4
            className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2"
            style={{ color: "var(--primary)", fontFamily: "var(--font-display)" }}
          >
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: "var(--primary)" }}
            />
            {CATEGORY_LABELS[code] || code}
          </h4>
          <div className="space-y-2">
            {grouped[code].map((skill, skillIdx) => (
              <motion.div
                key={`${code}-${skillIdx}`}
                className="rounded-lg px-4 py-3"
                style={{ background: "var(--secondary)" }}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: catIdx * 0.08 + skillIdx * 0.05,
                  duration: 0.3,
                }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium">
                    {skill.skill_name}
                  </span>
                  <span
                    className="text-xs font-semibold"
                    style={{ color: "var(--primary)" }}
                  >
                    {skill.confidence}%
                  </span>
                </div>
                {/* Confidence bar */}
                <div
                  className="w-full h-1.5 rounded-full overflow-hidden"
                  style={{ background: "var(--border)" }}
                >
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: "var(--primary)" }}
                    initial={{ width: 0 }}
                    animate={{ width: `${skill.confidence}%` }}
                    transition={{
                      delay: catIdx * 0.08 + skillIdx * 0.05 + 0.2,
                      duration: 0.6,
                      ease: "easeOut",
                    }}
                  />
                </div>
                {skill.evidence && (
                  <p
                    className="text-xs mt-1.5 leading-relaxed"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    {skill.evidence}
                  </p>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
