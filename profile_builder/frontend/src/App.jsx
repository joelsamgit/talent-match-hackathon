import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HeroPage from "./HeroPage";
import FlowApp from "./FlowApp";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HeroPage />} />
        <Route path="/app" element={<FlowApp />} />
      </Routes>
    </BrowserRouter>
  );
}