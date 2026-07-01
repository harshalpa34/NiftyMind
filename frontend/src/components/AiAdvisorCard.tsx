import React, { useState } from "react";
import { api, ApiError } from "../lib/api";
import Card from "./Card";
import { Sparkles, ShieldCheck } from "lucide-react";

interface AiAdvisorCardProps {
  portfolioId: string;
  holdingsCount: number;
}

export const AiAdvisorCard: React.FC<AiAdvisorCardProps> = ({ portfolioId, holdingsCount }) => {
  const [aiReport, setAiReport] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const handleGenerateAiReport = async () => {
    if (!portfolioId) return;
    setAiError(null);
    setAiLoading(true);

    try {
      // Set high timeout since Gemini QA on transcripts is slow
      const data = await api.get(`/portfolio-summary/${portfolioId}`, {
        timeout: 60000,
      });
      setAiReport(data);
    } catch (err) {
      setAiError(
        err instanceof ApiError ? err.message : "AI generation timed out or failed.",
      );
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div style={{ marginTop: "40px" }}>
      <Card
        title="AI Portfolio Advisor"
        actions={
          <button
            className="btn btn-primary"
            onClick={handleGenerateAiReport}
            disabled={aiLoading || holdingsCount === 0}
            style={{ padding: "8px 16px", fontSize: "0.85rem" }}
          >
            <Sparkles size={15} />
            {aiLoading ? "Generating Analysis..." : "Analyze Portfolio"}
          </button>
        }
      >
        {aiError && (
          <div
            style={{
              background: "var(--alert-error-bg)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              padding: "12px 16px",
              borderRadius: "8px",
              color: "var(--alert-error)",
              fontSize: "0.85rem",
              marginBottom: "20px",
            }}
          >
            {aiError}
          </div>
        )}

        {!aiReport ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-secondary)",
            }}
          >
            {aiLoading ? (
              <div>
                <div className="spinner" style={{ marginBottom: "15px" }}></div>
                Evaluating concentration risks, behavioral patterns, and corporate earnings calls...
              </div>
            ) : (
              "Click 'Analyze Portfolio' above to synthesize AI observations and corporate transcripts highlights."
            )}
          </div>
        ) : (
          <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* Disclaimer Alert */}
            <div
              style={{
                background: "rgba(99, 102, 241, 0.05)",
                border: "1px solid rgba(99, 102, 241, 0.2)",
                borderRadius: "8px",
                padding: "10px 14px",
                fontSize: "0.75rem",
                color: "#A5B4FC",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <ShieldCheck size={16} />
              <span>
                <strong>Compliance Disclaimer</strong>: Observations are generated using Large Language Models analyzing corporate transcripts. This is for research purposes and does not constitute certified SEBI financial advice.
              </span>
            </div>

            {/* AI Observations Text */}
            <div>
              <h3
                style={{
                  fontSize: "1.1rem",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  paddingBottom: "6px",
                }}
              >
                AI Advisor Observations
              </h3>
              <p
                style={{
                  color: "var(--text-primary)",
                  fontSize: "0.95rem",
                  lineHeight: "1.6",
                  whiteSpace: "pre-line",
                  margin: "8px 0 0",
                }}
              >
                {aiReport.ai_observations}
              </p>
            </div>

            {/* Corporate Highlights List */}
            {aiReport.corporate_highlights && (
              <div>
                <h3
                  style={{
                    fontSize: "1.1rem",
                    borderBottom: "1px solid rgba(255,255,255,0.05)",
                    paddingBottom: "6px",
                  }}
                >
                  Corporate Transcripts Highlights
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
                  {Object.entries(aiReport.corporate_highlights).map(([sym, hl]: any, index) => (
                    <div
                      key={index}
                      style={{
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid var(--surface-border)",
                        padding: "14px",
                        borderRadius: "8px",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 800,
                          color: "var(--secondary-color)",
                          marginRight: "12px",
                        }}
                      >
                        {sym}
                      </span>
                      <span
                        style={{
                          fontSize: "0.875rem",
                          color: "var(--text-secondary)",
                          lineHeight: "1.5",
                        }}
                      >
                        {hl}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
};
export default AiAdvisorCard;
