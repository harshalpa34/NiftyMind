import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import Card from "../components/Card";
import GuardrailAlerts from "../components/GuardrailAlerts";
import DangerZoneBanner from "../components/DangerZoneBanner";
import HoldingsCard from "../components/HoldingsCard";
import WatchdogCard from "../components/WatchdogCard";
import BulkImportCard from "../components/BulkImportCard";
import RiskGauge from "../components/RiskGauge";
import DependencyMapCard from "../components/DependencyMapCard";
import { ArrowLeft } from "lucide-react";

interface Holding {
  id: string;
  symbol: string;
  quantity: string;
  average_buy_price: string;
  current_price?: number;
  value?: number;
}

interface RiskMetrics {
  total_value: number;
  diversification_score: number;
  sector_exposure: Record<string, number>;
  concentration_risk?: any[];
}

export const PortfolioView: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Data states
  const [portfolio, setPortfolio] = useState<any>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [risk, setRisk] = useState<RiskMetrics | null>(null);
  const [flags, setFlags] = useState<any[]>([]);

  // UI states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // News Watchdog & Health states
  const [healthData, setHealthData] = useState<any>(null);
  const [dangerZone, setDangerZone] = useState<any>(null);
  const [watchdogRefreshing, setWatchdogRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"holdings" | "watchdog" | "dependencies">("holdings");


  const handleRefreshWatchdog = async () => {
    if (!id) return;
    setWatchdogRefreshing(true);
    try {
      const healthRes = await api.get(
        `/portfolios/${id}/health?force_refresh=true`,
      );
      setHealthData(healthRes);
    } catch (err) {
      console.error("Failed to refresh watchdog", err);
    } finally {
      setWatchdogRefreshing(false);
    }
  };

  const fetchAllData = async () => {
    if (!id) return;
    try {
      const [portData, riskData, flagData, healthRes, dangerRes] =
        await Promise.all([
          api.get(`/portfolios/${id}`),
          api.get(`/risk-analysis/${id}`),
          api.get(`/behavioral-analysis/${id}`),
          api.get(`/portfolios/${id}/health`),
          api.get(`/portfolios/${id}/danger-zone`),
        ]);

      setPortfolio(portData.portfolio);
      setHoldings(portData.holdings);
      setRisk(riskData);
      setFlags(flagData);
      setHealthData(healthRes);
      setDangerZone(dangerRes);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to fetch portfolio data.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, [id]);

  if (loading) {
    return (
      <div className="portfolio-loading-container">
        Loading portfolio dashboard details...
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="portfolio-error-container">
        <div
          className="glass-card"
          style={{ borderColor: "var(--alert-error)" }}
        >
          <h2 style={{ color: "var(--alert-error)", margin: 0 }}>
            Error Loading Portfolio
          </h2>
          <p style={{ color: "var(--text-secondary)", margin: "10px 0 20px" }}>
            {error || "Portfolio not found."}
          </p>
          <Link to="/" className="btn btn-secondary">
            <ArrowLeft size={16} /> Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="portfolio-view-container">
      {/* Danger Zone warning banner */}
      <DangerZoneBanner dangerZone={dangerZone} />

      {/* Navigation & Header */}
      <div className="portfolio-header-section">
        <Link to="/" className="back-link">
          <ArrowLeft size={14} /> Back to Portfolios
        </Link>
        <h1 className="portfolio-title">{portfolio.name}</h1>
        <p className="portfolio-desc">
          Allocation & Risk analytics calculated from your transactions history.
        </p>
      </div>

      <div className="portfolio-grid-layout">
        {/* Left Hand Column: Holdings & Watchdog Tabs */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Tabs Selector Header */}
          <div className="tabs-switcher-container">
            <button
              type="button"
              className={`tabs-switcher-btn ${activeTab === "holdings" ? "active" : ""}`}
              onClick={() => setActiveTab("holdings")}
            >
              Current Holdings
            </button>
            <button
              type="button"
              className={`tabs-switcher-btn ${activeTab === "watchdog" ? "active" : ""}`}
              onClick={() => setActiveTab("watchdog")}
            >
              AI Watchdog
            </button>
            <button
              type="button"
              className={`tabs-switcher-btn ${activeTab === "dependencies" ? "active" : ""}`}
              onClick={() => setActiveTab("dependencies")}
            >
              Dependency Explorer
            </button>
          </div>

          {activeTab === "holdings" ? (
            <HoldingsCard holdings={holdings} risk={risk} />
          ) : activeTab === "watchdog" ? (
            <WatchdogCard
              portfolioId={portfolio.id}
              healthData={healthData}
              watchdogRefreshing={watchdogRefreshing}
              handleRefreshWatchdog={handleRefreshWatchdog}
            />
          ) : (
            <DependencyMapCard
              portfolioId={portfolio.id}
              holdings={holdings}
            />
          )}
        </div>


        {/* Right Hand Column: Analytics & Import Card */}
        <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
          {/* Portfolio Diversification Gauge */}
          {risk && (
            <Card title="Portfolio Diversification">
              <RiskGauge score={risk.diversification_score} />
            </Card>
          )}

          {/* Behavioral Flags */}
          <Card title="Behavioral Guardrails">
            <GuardrailAlerts flags={flags} />
          </Card>

          {/* Bulk Import Card */}
          <BulkImportCard
            portfolioId={portfolio.id}
            onImportSuccess={fetchAllData}
          />
        </div>
      </div>
    </div>
  );
};

export default PortfolioView;
