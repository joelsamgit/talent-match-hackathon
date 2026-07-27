import React from "react";
import { motion } from "framer-motion";

const STEPS = [
  { num: 1, label: "JD Analysis" },
  { num: 2, label: "Resume" },
  { num: 3, label: "Profile" },
  { num: 4, label: "Talent Check" },
  { num: 5, label: "Skill Match" },
];

/**
 * Horizontal 5-step progress bar with animated amber fill.
 */
export default function ProgressBar({ currentStep, completedSteps = [] }) {
  return (
    <div className="w-full max-w-3xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between relative">
        {/* Background connecting line */}
        <div
          className="absolute top-5 left-0 right-0 h-0.5"
          style={{ background: "var(--border)", zIndex: 0 }}
        />
        {/* Animated filled line */}
        <motion.div
          className="absolute top-5 left-0 h-0.5"
          style={{
            background: "var(--primary)",
            zIndex: 1,
            originX: 0,
          }}
          initial={{ width: "0%" }}
          animate={{
            width: `${((Math.min(currentStep, 5) - 1) / 4) * 100}%`,
          }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />

        {STEPS.map((step) => {
          const isActive = step.num === currentStep;
          const isCompleted = completedSteps.includes(step.num) || step.num < currentStep;

          return (
            <div
              key={step.num}
              className="flex flex-col items-center relative z-10"
              style={{ minWidth: 64 }}
            >
              <motion.div
                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold"
                style={{
                  fontFamily: "var(--font-display)",
                  background: isCompleted
                    ? "var(--primary)"
                    : isActive
                    ? "var(--primary)"
                    : "var(--secondary)",
                  color: isCompleted || isActive
                    ? "var(--primary-foreground)"
                    : "var(--muted-foreground)",
                  border: isActive
                    ? "2px solid var(--primary)"
                    : "2px solid var(--border)",
                }}
                animate={{
                  scale: isActive ? 1.15 : 1,
                }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                {isCompleted && !isActive ? (
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="3,8 7,12 13,4" />
                  </svg>
                ) : (
                  step.num
                )}
              </motion.div>
              <span
                className="mt-2 text-xs font-medium"
                style={{
                  color: isActive
                    ? "var(--primary)"
                    : isCompleted
                    ? "var(--foreground)"
                    : "var(--muted-foreground)",
                  fontFamily: "var(--font-body)",
                }}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
