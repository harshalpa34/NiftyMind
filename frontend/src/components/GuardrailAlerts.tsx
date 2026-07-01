import React from "react";
import { AlertTriangle, CheckCircle, ShieldAlert } from "lucide-react";

interface Flag {
  flag_type: string;
  severity: "HIGH" | "MEDIUM" | string;
  description: string;
  detected_at?: string;
}

interface GuardrailAlertsProps {
  flags: Flag[];
}

export const GuardrailAlerts: React.FC<GuardrailAlertsProps> = ({ flags }) => {
  if (!flags || flags.length === 0) {
    return (
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        background: "rgba(16, 185, 129, 0.05)",
        border: "1px solid rgba(16, 185, 129, 0.2)",
        padding: "16px",
        borderRadius: "12px",
        color: "var(--alert-success)",
      }}>
        <CheckCircle size={20} />
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>All Behavioral Guardrails Clear</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            No bad habits, FOMO, or excessive concentration detected in recent transactions.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {flags.map((flag, idx) => {
        const isHigh = flag.severity === "HIGH";
        const alertBg = isHigh ? "var(--alert-error-bg)" : "var(--alert-warning-bg)";
        const alertBorder = isHigh ? "rgba(239, 68, 68, 0.25)" : "rgba(245, 158, 11, 0.25)";
        const alertColor = isHigh ? "var(--alert-error)" : "var(--alert-warning)";
        const Icon = isHigh ? ShieldAlert : AlertTriangle;

        return (
          <div 
            key={idx}
            className="animate-fade-in"
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "12px",
              background: alertBg,
              border: `1px solid ${alertBorder}`,
              padding: "16px",
              borderRadius: "12px",
              animationDelay: `${idx * 0.1}s`,
            }}
          >
            <div style={{ color: alertColor, marginTop: "2px", display: "flex" }}>
              <Icon size={18} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="font-outfit" style={{ fontWeight: 700, fontSize: "0.95rem", color: alertColor }}>
                  {flag.flag_type.replace("_", " ")}
                </span>
                <span style={{
                  fontSize: "0.7rem",
                  background: isHigh ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                  color: alertColor,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                }}>
                  {flag.severity}
                </span>
              </div>
              <p style={{
                margin: "6px 0 0",
                fontSize: "0.85rem",
                color: "var(--text-primary)",
                lineHeight: "1.4",
              }}>
                {flag.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
export default GuardrailAlerts;
