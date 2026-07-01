import React from "react";
import { AlertTriangle } from "lucide-react";

interface DangerZoneBannerProps {
  dangerZone: {
    danger_stocks: string[];
    reasons: Record<string, string>;
    recommended_action: string;
  } | null;
}

export const DangerZoneBanner: React.FC<DangerZoneBannerProps> = ({ dangerZone }) => {
  if (!dangerZone || !dangerZone.danger_stocks || dangerZone.danger_stocks.length === 0) {
    return null;
  }

  return (
    <div className="danger-zone-banner">
      <AlertTriangle
        size={24}
        color="var(--alert-error)"
        className="danger-icon"
      />
      <div className="danger-content">
        <h3>Watchdog Warning: Danger Zone Detected</h3>
        <p>
          Critical negative indicators have been flagged for:{" "}
          {dangerZone.danger_stocks.join(", ")}
        </p>
        <ul>
          {Object.entries(dangerZone.reasons).map(([sym, reason]: any) => (
            <li key={sym}>
              <strong>{sym}</strong>: {reason}
            </li>
          ))}
        </ul>
        <div className="recommendation">
          <strong>Recommended Action</strong>: {dangerZone.recommended_action}
        </div>
      </div>
    </div>
  );
};
export default DangerZoneBanner;
