import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

/**
 * Animated radial progress ring that counts up from 0 to value.
 */
export default function RadialScore({
  value = 0,
  label = "Score",
  size = 180,
  strokeWidth = 10,
  color,
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const scoreColor =
    color || (value >= 70 ? "var(--success)" : value >= 40 ? "var(--primary)" : "var(--danger)");

  // Animate the displayed number counting up
  useEffect(() => {
    setDisplayValue(0);
    const duration = 1200;
    const steps = 40;
    const increment = value / steps;
    let current = 0;
    const interval = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(interval);
      } else {
        setDisplayValue(Math.round(current));
      }
    }, duration / steps);
    return () => clearInterval(interval);
  }, [value]);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth={strokeWidth}
          />
          {/* Animated foreground arc */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={scoreColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{
              strokeDashoffset: circumference - (value / 100) * circumference,
            }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-4xl font-bold"
            style={{ fontFamily: "var(--font-display)", color: scoreColor }}
          >
            {displayValue}%
          </span>
          <span
            className="text-xs mt-1"
            style={{ color: "var(--muted-foreground)" }}
          >
            {label}
          </span>
        </div>
      </div>
    </div>
  );
}
