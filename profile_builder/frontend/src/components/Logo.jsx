import React from "react";

/**
 * RADIX wordmark logo.
 * The crossbar of the "A" is rendered in amber accent instead of white.
 */
export default function Logo({ className = "" }) {
  return (
    <div className={`flex items-baseline gap-2 ${className}`}>
      <span
        className="text-2xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {/* R */}
        <span className="text-[var(--foreground)]">R</span>
        {/* A with amber crossbar — use SVG for the A */}
        <svg
          viewBox="0 0 36 40"
          className="inline-block"
          style={{ width: "0.8em", height: "1em", verticalAlign: "baseline", marginBottom: "-0.05em" }}
          aria-hidden="true"
        >
          {/* Left leg */}
          <line x1="3" y1="38" x2="18" y2="2" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" />
          {/* Right leg */}
          <line x1="33" y1="38" x2="18" y2="2" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" />
          {/* Amber crossbar */}
          <line x1="9" y1="25" x2="27" y2="25" stroke="var(--primary)" strokeWidth="4" strokeLinecap="round" />
        </svg>
        {/* DIX */}
        <span className="text-[var(--foreground)]">DIX</span>
      </span>
      <span
        className="text-xs tracking-wide"
        style={{ color: "var(--muted-foreground)", fontFamily: "var(--font-body)" }}
      >
        Talent Match
      </span>
    </div>
  );
}
