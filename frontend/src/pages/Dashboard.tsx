import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import Card from "../components/Card";
import { Briefcase, Plus, Trash2, TrendingUp, ArrowRight } from "lucide-react";

interface Portfolio {
  id: string;
  name: string;
  created_at: string;
}

export const Dashboard: React.FC = () => {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);

  const fetchPortfolios = async () => {
    try {
      const data = await api.get("/portfolios");
      setPortfolios(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to fetch portfolios.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPortfolioName.trim()) return;

    setError(null);
    setCreateLoading(true);

    try {
      const newPort = await api.post("/portfolios", { name: newPortfolioName });
      setPortfolios((prev) => [newPort, ...prev]);
      setNewPortfolioName("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to create portfolio.");
      }
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDeletePortfolio = async (id: string, e: React.MouseEvent) => {
    e.preventDefault(); // Prevent navigating to details
    if (!window.confirm("Are you sure you want to delete this portfolio? This will remove all holdings and transactions.")) {
      return;
    }

    try {
      await api.delete(`/portfolios/${id}`);
      setPortfolios((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Failed to delete portfolio");
    }
  };

  return (
    <div style={{ padding: "40px", maxWidth: "1200px", margin: "0 auto" }}>
      
      {/* Top Banner Stats */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "35px",
      }}>
        <div>
          <h1 style={{ margin: 0 }}>My Portfolios</h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: "0.95rem" }}>
            Track allocations, HHI diversification indices, and behavioral guardrails.
          </p>
        </div>
      </div>

      {error && (
        <div style={{
          background: "var(--alert-error-bg)",
          border: "1px solid rgba(239, 68, 68, 0.2)",
          padding: "16px",
          borderRadius: "12px",
          color: "var(--alert-error)",
          marginBottom: "30px",
        }}>
          {error}
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 340px",
        gap: "30px",
        alignItems: "start",
      }}>
        
        {/* Portfolios list Grid */}
        <div>
          {loading ? (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>
              Loading portfolios...
            </div>
          ) : portfolios.length === 0 ? (
            <div style={{
              background: "rgba(255, 255, 255, 0.01)",
              border: "2px dashed var(--surface-border)",
              borderRadius: "16px",
              padding: "60px 40px",
              textAlign: "center",
            }}>
              <Briefcase size={40} color="var(--text-secondary)" style={{ marginBottom: "16px" }} />
              <h3 style={{ margin: "0 0 8px", fontSize: "1.2rem", fontWeight: 600 }}>No Portfolios Found</h3>
              <p style={{ color: "var(--text-secondary)", maxWidth: "400px", margin: "0 auto 20px", fontSize: "0.85rem", lineHeight: "1.4" }}>
                Create your first growth portfolio on the right to start logging stock transactions and analyzing your holdings.
              </p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
              {portfolios.map((portfolio) => (
                <Link 
                  key={portfolio.id}
                  to={`/portfolio/${portfolio.id}`} 
                  style={{ textDecoration: "none", color: "inherit" }}
                >
                  <Card 
                    title={portfolio.name}
                    actions={
                      <button 
                        onClick={(e) => handleDeletePortfolio(portfolio.id, e)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--text-secondary)",
                          transition: "color 0.2s",
                          padding: "4px",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--alert-error)")}
                        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
                      >
                        <Trash2 size={16} />
                      </button>
                    }
                  >
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginTop: "10px",
                    }}>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                        Created: {new Date(portfolio.created_at).toLocaleDateString()}
                      </span>
                      <span style={{
                        color: "var(--primary-color)",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}>
                        View details
                        <ArrowRight size={14} />
                      </span>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar Manager */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {/* Create Portfolio Form */}
          <Card title="Create Portfolio">
            <form onSubmit={handleCreatePortfolio}>
              <div className="form-group">
                <label>Portfolio Name</label>
                <input 
                  type="text" 
                  placeholder="e.g. Long-term Equity" 
                  value={newPortfolioName}
                  onChange={(e) => setNewPortfolioName(e.target.value)}
                  required
                />
              </div>
              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={createLoading || !newPortfolioName.trim()}
                style={{ width: "100%", gap: "6px" }}
              >
                <Plus size={16} />
                {createLoading ? "Creating..." : "Create Portfolio"}
              </button>
            </form>
          </Card>

          {/* Tips Info Panel */}
          <div className="glass-card" style={{ background: "rgba(99, 102, 241, 0.02)", border: "1px solid rgba(99, 102, 241, 0.1)" }}>
            <h3 style={{ margin: "0 0 10px", fontSize: "1rem", color: "#A5B4FC", display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} />
              Platform Guidelines
            </h3>
            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              <li style={{ marginBottom: "8px" }}>Upload CSV or Excel spreadsheets to bulk import your active holdings.</li>
              <li style={{ marginBottom: "8px" }}>AI Watchdog monitors daily news sentiment, stop-loss suggestions, and quarterly targets.</li>
              <li style={{ marginBottom: "8px" }}>Danger Zone alerts flag high-risk holdings with severe negative sentiment.</li>
              <li>Behavioral Guardrails track visual alerts for cognitive biases in your asset split.</li>
            </ul>
          </div>

        </div>

      </div>

    </div>
  );
};
export default Dashboard;
