import React from "react";
import { Link } from "react-router-dom";
import Logo from "./components/Logo";

/**
 * Landing hero page at "/".
 */
export default function HeroPage() {
  return (
    <div className="relative min-h-dvh flex flex-col overflow-hidden">
      {/* ── Background ── */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, hsla(75,25%,16%,1) 0%, var(--background) 70%)",
        }}
      />

      {/* ── Nav Bar ── */}
      <nav className="liquid-glass relative z-10 flex items-center justify-between px-8 py-5 max-w-7xl mx-auto w-full">
        <Logo />
        <Link
          to="/app"
          className="liquid-glass rounded-full px-6 py-2.5 text-sm font-medium cursor-pointer transition-transform hover:scale-[1.03]"
          style={{ color: "var(--foreground)", textDecoration: "none" }}
        >
          Check Your Readiness
        </Link>
      </nav>

      {/* ── Hero Section ── */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-6 pt-32 pb-40">
        <h1
          className="animate-fade-rise text-5xl sm:text-7xl md:text-8xl leading-[0.95] tracking-tight font-normal"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Know exactly how{" "}
          <span style={{ color: "var(--primary)" }}>ready</span> you are.
        </h1>

        <p
          className="animate-fade-rise-delay text-base sm:text-lg max-w-2xl mt-8 leading-relaxed"
          style={{ color: "var(--muted-foreground)" }}
        >
          Upload your resume, pick a job, and see the real gap — skill by skill
          — before you walk into the interview.
        </p>

        <Link
          to="/app"
          className="animate-fade-rise-delay-2 liquid-glass rounded-full px-14 py-5 text-base font-medium mt-12 cursor-pointer transition-transform hover:scale-[1.03] inline-block"
          style={{ color: "var(--foreground)", textDecoration: "none" }}
        >
          Check Your Readiness
        </Link>
      </main>

      {/* ── Footer ── */}
      <footer
        className="relative z-10 text-center pb-8 text-xs"
        style={{ color: "var(--muted-foreground)", opacity: 0.6 }}
      >
        Built by Team fiveB
      </footer>
    </div>
  );
}
