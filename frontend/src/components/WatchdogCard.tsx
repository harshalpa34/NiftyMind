import React, { useState } from "react";
import Card from "./Card";
import { RefreshCw, TrendingUp, ChevronUp, ChevronDown } from "lucide-react";

interface WatchdogCardProps {
  portfolioId: string;
  healthData: any;
  watchdogRefreshing: boolean;
  handleRefreshWatchdog: () => Promise<void>;
}

export const WatchdogCard: React.FC<WatchdogCardProps> = ({
  portfolioId,
  healthData,
  watchdogRefreshing,
  handleRefreshWatchdog,
}) => {
  const [expandedStockNews, setExpandedStockNews] = useState<Record<string, boolean>>({});

  const toggleStockNews = (symbol: string) => {
    setExpandedStockNews((prev) => ({
      ...prev,
      [symbol]: !prev[symbol],
    }));
  };

  if (!healthData || !healthData.holdings || healthData.holdings.length === 0) {
    return null;
  }

  const totalNewsCount = healthData.holdings.reduce(
    (sum: number, stock: any) => sum + (stock.news_count_24h || 0),
    0,
  );

  return (
    <div>
      <Card
        title="AI Watchdog: Portfolio Health & News Sentiment"
        actions={
          <div className="watchdog-actions">
            {/* Refresh Watchdog Button */}
            <button
              type="button"
              className="refresh-btn"
              onClick={handleRefreshWatchdog}
              disabled={watchdogRefreshing}
            >
              <RefreshCw
                size={13}
                className={watchdogRefreshing ? "animate-spin" : ""}
              />
              {watchdogRefreshing ? "Refreshing..." : "Refresh Watchdog"}
            </button>

            <div className="health-score-wrapper">
              <span className="label">Portfolio Health Score:</span>
              <span
                className={`score ${
                  healthData.health_score > 75
                    ? "high"
                    : healthData.health_score > 40
                      ? "medium"
                      : "low"
                }`}
              >
                {healthData.health_score}%
              </span>
            </div>
          </div>
        }
      >
        <div className="watchdog-container">
          {/* Summary Stats */}
          <div className="watchdog-summary-stats">
            <div>
              <div className="stat-label">Portfolio Sentiment Watch</div>
              <span
                className={`stat-value ${
                  healthData.overall_sentiment === "POSITIVE"
                    ? "positive"
                    : healthData.overall_sentiment === "NEGATIVE"
                      ? "negative"
                      : "neutral"
                }`}
              >
                {healthData.overall_sentiment}
              </span>
            </div>
            <div>
              <div className="stat-label">24h Total News Articles</div>
              <span className="stat-value">{totalNewsCount} items</span>
            </div>
          </div>

          {/* Stock News & Suggestions list */}
          <div className="watchdog-holdings-list">
            {healthData.holdings.map((stock: any) => {
              const hasTargets = stock.quarterly_targets;
              const isExpanded = !!expandedStockNews[stock.symbol];
              return (
                <div key={stock.symbol} className="watchdog-stock-item">
                  {/* Stock Summary Header */}
                  <div className="stock-header">
                    <div>
                      <span className="symbol">{stock.symbol}</span>
                      <span
                        className={`badge ${
                          stock.current_sentiment === "POSITIVE"
                            ? "badge-success"
                            : stock.current_sentiment === "NEGATIVE"
                              ? "badge-danger"
                              : ""
                        } badge-sentiment`}
                      >
                        {stock.current_sentiment}
                      </span>
                      <div className="holdings-meta">
                        Holdings: {stock.qty} shares @ avg ₹
                        {stock.avg_price.toFixed(2)} (Current: ₹
                        {stock.current_price.toFixed(2)})
                      </div>
                    </div>

                    <div className="right-info">
                      <span
                        className={`badge ${
                          stock.risk_signal === "EXIT"
                            ? "badge-danger"
                            : stock.risk_signal === "CAUTION"
                              ? "badge-risk caution"
                              : "badge-success"
                        }`}
                      >
                        Risk Alert: {stock.risk_signal || "HOLD"}
                      </span>
                      <div className="stop-loss">
                        Suggested SL:{" "}
                        {stock.suggested_stop_loss
                          ? `₹${stock.suggested_stop_loss.toFixed(2)}`
                          : "Calculating..."}
                      </div>
                    </div>
                  </div>

                  {/* Rationale & Suggestions */}
                  <div style={{ marginBottom: "16px" }}>
                    <p className="recommendation-text">
                      <strong>AI Recommendation</strong>: {stock.reasoning}
                    </p>
                  </div>

                  {/* Target Timeline Progress */}
                  {hasTargets && (
                    <div className="quarterly-targets-panel">
                      <div className="targets-header">
                        <TrendingUp size={14} color="var(--primary-color)" />
                        AI Expected Quarterly Targets
                      </div>

                      <div className="targets-grid">
                        <div className="target-box">
                          <div className="q-label">Q1 (3m) Target</div>
                          <div className="q-val q1">
                            ₹
                            {stock.quarterly_targets.q1_target
                              ? parseFloat(stock.quarterly_targets.q1_target).toFixed(1)
                              : "-"}
                          </div>
                        </div>
                        <div className="target-box">
                          <div className="q-label">Q2 (6m) Target</div>
                          <div className="q-val q2">
                            ₹
                            {stock.quarterly_targets.q2_target
                              ? parseFloat(stock.quarterly_targets.q2_target).toFixed(1)
                              : "-"}
                          </div>
                        </div>
                        <div className="target-box">
                          <div className="q-label">Q3 (9m) Target</div>
                          <div className="q-val q3">
                            ₹
                            {stock.quarterly_targets.q3_target
                              ? parseFloat(stock.quarterly_targets.q3_target).toFixed(1)
                              : "-"}
                          </div>
                        </div>
                        <div className="target-box">
                          <div className="q-label">Q4 (12m) Target</div>
                          <div className="q-val q4">
                            ₹
                            {stock.quarterly_targets.q4_target
                              ? parseFloat(stock.quarterly_targets.q4_target).toFixed(1)
                              : "-"}
                          </div>
                        </div>
                      </div>

                      <p className="rationale-text">
                        <strong>Targets Rationale</strong>:{" "}
                        {stock.quarterly_targets.target_rationale}
                      </p>
                    </div>
                  )}

                  {/* Toggle News list */}
                  <div>
                    <button
                      type="button"
                      onClick={() => toggleStockNews(stock.symbol)}
                      className="news-accordion-btn"
                    >
                      {isExpanded ? (
                        <ChevronUp size={14} />
                      ) : (
                        <ChevronDown size={14} />
                      )}
                      {isExpanded
                        ? "Hide Latest News"
                        : `Show News Watchdog (${stock.news_count_24h || 0} articles)`}
                    </button>

                    {isExpanded && (
                      <div className="news-items-list">
                        {!stock.top_news || stock.top_news.length === 0 ? (
                          <div className="news-empty">
                            No news articles tracked for {stock.symbol} in the last 24 hours.
                          </div>
                        ) : (
                          stock.top_news.map((item: any, nIdx: number) => (
                            <div key={nIdx} className="news-item-card">
                              <div className="news-header">
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="news-title"
                                >
                                  {item.title}
                                </a>
                                <span
                                  className={`badge ${
                                    item.sentiment === "POSITIVE"
                                      ? "badge-success"
                                      : item.sentiment === "NEGATIVE"
                                        ? "badge-danger"
                                        : ""
                                  } sentiment-badge`}
                                >
                                  {item.sentiment}
                                </span>
                              </div>

                              <div className="news-meta">
                                {item.source} •{" "}
                                {new Date(item.published_at).toLocaleString()} • Impact:{" "}
                                {item.impact_level} ({item.impact_type})
                              </div>

                              <p className="news-summary">
                                <strong>AI Analysis</strong>: {item.ai_summary}
                              </p>
                              {item.price_effect && (
                                <div
                                  className={`news-effect ${
                                    item.sentiment === "NEGATIVE" ? "negative" : "positive"
                                  }`}
                                >
                                  Effect: {item.price_effect}
                                </div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>
    </div>
  );
};
export default WatchdogCard;
