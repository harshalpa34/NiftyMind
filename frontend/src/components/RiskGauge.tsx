import React from "react";
import { ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";

interface RiskGaugeProps {
  score: number;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ score }) => {
  // Determine color and status text based on score
  let statusColor = "var(--alert-error)";
  let statusText = "High Concentration";
  let statusDesc = "Your assets are concentrated in very few stocks. High volatility risk.";
  let Icon = ShieldAlert;

  if (score >= 70) {
    statusColor = "var(--alert-success)";
    statusText = "Excellent Diversification";
    statusDesc = "Well-balanced portfolio. Standard market exposure.";
    Icon = ShieldCheck;
  } else if (score >= 40) {
    statusColor = "var(--alert-warning)";
    statusText = "Moderate Exposure";
    statusDesc = "Decent spread, but could benefit from sector reallocation.";
    Icon = AlertTriangle;
  }

  return (
    <div style={{ textAlign: "center", padding: "10px 0" }}>
      {/* Visual Circle Gauge */}
      <div style={{
        position: "relative",
        width: "140px",
        height: "140px",
        margin: "0 auto 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        {/* Background Circle */}
        <svg width="100%" height="100%" viewBox="0 0 100 100" style={{ transform: "rotate(-90deg)" }}>
          <circle 
            cx="50" 
            cy="50" 
            r="42" 
            fill="transparent" 
            stroke="rgba(255,255,255,0.05)" 
            strokeWidth="8"
          />
          {/* Progress Circle */}
          <circle 
            cx="50" 
            cy="50" 
            r="42" 
            fill="transparent" 
            stroke={statusColor} 
            strokeWidth="8"
            strokeDasharray={2 * Math.PI * 42}
            strokeDashoffset={2 * Math.PI * 42 * (1 - score / 100)}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>

        {/* Center Text */}
        <div style={{ position: "absolute", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <span style={{ fontSize: "2rem", fontWeight: 800, fontFamily: "Outfit, sans-serif" }}>
            {score}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 600 }}>
            HHI Index
          </span>
        </div>
      </div>

      {/* Info Panel */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        background: "rgba(255, 255, 255, 0.02)",
        padding: "12px 16px",
        borderRadius: "8px",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        textAlign: "left",
      }}>
        <div style={{
          background: `rgba(${statusColor === "var(--alert-success)" ? "16, 185, 129" : statusColor === "var(--alert-warning)" ? "245, 158, 11" : "239, 68, 68"}, 0.1)`,
          padding: "8px",
          borderRadius: "8px",
          display: "flex",
          color: statusColor,
        }}>
          <Icon size={22} />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: "0.95rem", color: statusColor }}>
            {statusText}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px", lineHeight: "1.3" }}>
            {statusDesc}
          </div>
        </div>
      </div>
    </div>
  );
};
export default RiskGauge;
