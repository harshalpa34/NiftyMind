import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, ShieldAlert, User, LayoutDashboard, Search } from "lucide-react";

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav style={{
      background: "rgba(11, 15, 25, 0.8)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
      padding: "16px 40px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      position: "sticky",
      top: 0,
      zIndex: 100,
    }}>
      <Link to="/" style={{
        textDecoration: "none",
        display: "flex",
        alignItems: "center",
        gap: "10px",
      }}>
        <div style={{
          background: "linear-gradient(135deg, #6366F1 0%, #14B8A6 100%)",
          width: "36px",
          height: "36px",
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          boxShadow: "0 0 15px rgba(99, 102, 241, 0.4)",
        }}>
          <ShieldAlert size={20} />
        </div>
        <span className="font-outfit" style={{
          fontSize: "1.4rem",
          fontWeight: 800,
          background: "linear-gradient(135deg, #FFF 0%, #E0E7FF 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          letterSpacing: "-0.02em",
        }}>
          NiftyMind
        </span>
        <span style={{
          fontSize: "0.75rem",
          background: "rgba(99, 102, 241, 0.15)",
          color: "#A5B4FC",
          padding: "2px 8px",
          borderRadius: "12px",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          fontWeight: 600,
        }}>
          Advisor
        </span>
      </Link>

      {user && (
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          {/* Navigation Links */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginRight: "16px" }}>
            <Link 
              to="/" 
              style={{
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.9rem",
                fontWeight: 600,
                color: location.pathname === "/" ? "var(--primary-color)" : "var(--text-secondary)",
                transition: "color 0.2s",
              }}
            >
              <LayoutDashboard size={16} />
              Dashboard
            </Link>

            <Link 
              to="/rag" 
              style={{
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.9rem",
                fontWeight: 600,
                color: location.pathname === "/rag" ? "var(--primary-color)" : "var(--text-secondary)",
                transition: "color 0.2s",
              }}
            >
              <Search size={16} />
              Corporate RAG
            </Link>
          </div>

          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(255, 255, 255, 0.03)",
            padding: "6px 14px",
            borderRadius: "20px",
            border: "1px solid rgba(255, 255, 255, 0.05)",
          }}>
            <User size={16} color="#A5B4FC" />
            <span style={{ fontSize: "0.9rem", fontWeight: 500 }}>
              {user.full_name || user.email}
            </span>
          </div>

          <button 
            className="btn btn-secondary" 
            onClick={handleLogout}
            style={{
              padding: "8px 16px",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <LogOut size={15} />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
};
export default Navbar;
