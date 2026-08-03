import React, { useState, useEffect } from "react";
import { api, ApiError } from "../lib/api";
import { ArrowLeftRight, ArrowRight, Layers } from "lucide-react";

interface Edge {
  source: string;
  target: string;
  type: string;
  properties: {
    category?: string;
    reliance?: string;
  };
}

interface Holding {
  id: string;
  symbol: string;
  quantity: string;
  average_buy_price: string;
}

interface DependencyMapCardProps {
  portfolioId: string;
  holdings: Holding[];
}

export const DependencyMapCard: React.FC<DependencyMapCardProps> = ({
  portfolioId,
  holdings,
}) => {
  const [dependencies, setDependencies] = useState<Edge[]>([]);
  const [activeSymbol, setActiveSymbol] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDependencies = async () => {
      try {
        const res = await api.get(
          `/graph/portfolio/${portfolioId}/dependencies`,
        );
        setDependencies(res);
        if (holdings.length > 0) {
          setActiveSymbol(holdings[0].symbol.toUpperCase());
        }
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Failed to load dependencies.",
        );
      } finally {
        setLoading(false);
      }
    };
    fetchDependencies();
  }, [portfolioId, holdings]);

  if (loading) {
    return (
      <div
        style={{
          padding: "30px",
          textAlign: "center",
          color: "var(--text-secondary)",
        }}
      >
        Loading dependency graph...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "20px", color: "var(--alert-error)" }}>
        {error}
      </div>
    );
  }

  if (holdings.length === 0) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--text-secondary)",
        }}
      >
        No holdings found. Import a portfolio statement to explore dependencies.
      </div>
    );
  }

  const activeSymbolUpper = activeSymbol.toUpperCase();

  // Filter relationships for the active holding
  const sectorEdge = dependencies.find(
    (d) => d.source === activeSymbolUpper && d.type === "BELONGS_TO",
  );
  const sectorName = sectorEdge ? sectorEdge.target : "Unmapped Sector";

  const competitors = dependencies
    .filter(
      (d) =>
        d.type === "COMPETES_WITH" &&
        (d.source === activeSymbolUpper || d.target === activeSymbolUpper),
    )
    .map((d) => (d.source === activeSymbolUpper ? d.target : d.source));

  const clients = dependencies.filter(
    (d) => d.type === "VENDOR_OF" && d.source === activeSymbolUpper,
  );
  const vendors = dependencies.filter(
    (d) => d.type === "VENDOR_OF" && d.target === activeSymbolUpper,
  );

  const getRelianceColor = (reliance?: string) => {
    switch (reliance?.toUpperCase()) {
      case "HIGH":
        return "#ef4444";
      case "MEDIUM":
        return "#f97316";
      case "LOW":
        return "#10b981";
      default:
        return "var(--text-secondary)";
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: "25px",
        borderRadius: "16px",
        background: "var(--surface-card)",
      }}
    >
      {/* Header & Stock Selector */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "25px",
          flexWrap: "wrap",
          gap: "15px",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 600 }}>
            Stock Dependency Explorer
          </h3>
          <p
            style={{
              margin: "4px 0 0",
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
            }}
          >
            Explore clients, vendors, competitors, and sector linkages
            dynamically from your holdings.
          </p>
        </div>

        <div>
          <select
            value={activeSymbol}
            onChange={(e) => setActiveSymbol(e.target.value)}
            style={{
              padding: "8px 16px",
              borderRadius: "10px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid var(--surface-border)",
              color: "var(--text-primary)",
              outline: "none",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            {holdings.map((h) => (
              <option
                key={h.id}
                value={h.symbol.toUpperCase()}
                style={{ background: "#18181b" }}
              >
                {h.symbol.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Network Layout Map */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1.2fr 1fr",
          gap: "20px",
          alignItems: "stretch",
          marginTop: "10px",
          minHeight: "350px",
        }}
      >
        {/* Left Column: Suppliers/Vendors */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "15px",
            background: "rgba(255, 255, 255, 0.01)",
            border: "1px solid var(--surface-border)",
            borderRadius: "12px",
            padding: "15px",
          }}
        >
          <h4
            style={{
              margin: "0 0 5px",
              fontSize: "0.9rem",
              color: "var(--text-secondary)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <ArrowRight size={16} color="var(--primary-color)" /> Suppliers /
            Vendors
          </h4>

          {vendors.length === 0 ? (
            <div
              style={{
                margin: "auto",
                color: "var(--text-secondary)",
                fontSize: "0.8rem",
                fontStyle: "italic",
                textAlign: "center",
              }}
            >
              No critical suppliers mapped.
            </div>
          ) : (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              {vendors.map((v, i) => (
                <div
                  key={i}
                  className="glass-card"
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--surface-border)",
                    background: "rgba(255, 255, 255, 0.02)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                      {v.source}
                    </span>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        color: getRelianceColor(v.properties.reliance),
                        border: `1px solid ${getRelianceColor(v.properties.reliance)}`,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      {v.properties.reliance} Reliance
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: "0.75rem",
                      color: "var(--text-secondary)",
                      marginTop: "6px",
                    }}
                  >
                    {v.properties.category}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Center Column: Sector & Active Ticker */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "20px",
            padding: "20px 10px",
          }}
        >
          {/* Sector Card */}
          <div
            style={{
              background: "rgba(14, 165, 233, 0.05)",
              border: "1px solid rgba(14, 165, 233, 0.2)",
              borderRadius: "12px",
              padding: "12px 20px",
              textAlign: "center",
              width: "100%",
              maxWidth: "240px",
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.1)",
            }}
          >
            <Layers size={20} color="#0ea5e9" style={{ marginBottom: "6px" }} />
            <div
              style={{
                fontSize: "0.7rem",
                textTransform: "uppercase",
                tracking: "0.05em",
                color: "var(--text-secondary)",
              }}
            >
              Sector
            </div>
            <div
              style={{
                fontWeight: 600,
                fontSize: "0.95rem",
                color: "var(--text-primary)",
                marginTop: "2px",
              }}
            >
              {sectorName}
            </div>
          </div>

          {/* Active Company Node */}
          <div
            style={{
              background: "rgba(99, 102, 241, 0.1)",
              border: "2px solid var(--primary-color)",
              borderRadius: "50%",
              width: "120px",
              height: "120px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              boxShadow: "0 0 30px rgba(99, 102, 241, 0.2)",
              animation: "pulse 2s infinite alternate",
              zIndex: 2,
            }}
          >
            <span
              style={{
                fontSize: "1rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                textOverflow: "ellipsis",
                textAlign: "center",
              }}
            >
              {activeSymbolUpper}
            </span>
          </div>

          {/* Competitors List */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.01)",
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              padding: "12px 20px",
              width: "100%",
              maxWidth: "240px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-secondary)",
                marginBottom: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
              }}
            >
              <ArrowLeftRight size={14} color="var(--primary-color)" />{" "}
              Competitors
            </div>
            {competitors.length === 0 ? (
              <div
                style={{
                  fontSize: "0.75rem",
                  fontStyle: "italic",
                  color: "var(--text-secondary)",
                }}
              >
                No key competitors mapped.
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  justifyContent: "center",
                  flexWrap: "wrap",
                }}
              >
                {competitors.map((comp, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid var(--surface-border)",
                      padding: "4px 10px",
                      borderRadius: "6px",
                    }}
                  >
                    {comp}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Clients/Customers */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "15px",
            background: "rgba(255, 255, 255, 0.01)",
            border: "1px solid var(--surface-border)",
            borderRadius: "12px",
            padding: "15px",
          }}
        >
          <h4
            style={{
              margin: "0 0 5px",
              fontSize: "0.9rem",
              color: "var(--text-secondary)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            Clients / Customers{" "}
            <ArrowRight size={16} color="var(--primary-color)" />
          </h4>

          {clients.length === 0 ? (
            <div
              style={{
                margin: "auto",
                color: "var(--text-secondary)",
                fontSize: "0.8rem",
                fontStyle: "italic",
                textAlign: "center",
              }}
            >
              No critical clients mapped.
            </div>
          ) : (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              {clients.map((c, i) => (
                <div
                  key={i}
                  className="glass-card"
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--surface-border)",
                    background: "rgba(255, 255, 255, 0.02)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                      {c.target}
                    </span>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        color: getRelianceColor(c.properties.reliance),
                        border: `1px solid ${getRelianceColor(c.properties.reliance)}`,
                        padding: "2px 3px",
                        borderRadius: "4px",
                        marginLeft: "5px",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {c.properties.reliance} Imp
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: "0.75rem",
                      color: "var(--text-secondary)",
                      marginTop: "6px",
                    }}
                  >
                    {c.properties.category}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DependencyMapCard;
