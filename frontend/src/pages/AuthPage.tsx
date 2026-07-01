import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";
import { Lock, Mail, User, ShieldAlert } from "lucide-react";

export const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "calc(100vh - 80px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
    }}>
      <div className="glass-card animate-fade-in" style={{ width: "100%", maxWidth: "440px" }}>
        
        {/* Header Logo */}
        <div style={{ textAlign: "center", marginBottom: "30px" }}>
          <div style={{
            background: "linear-gradient(135deg, #6366F1 0%, #14B8A6 100%)",
            width: "50px",
            height: "50px",
            borderRadius: "12px",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            marginBottom: "12px",
            boxShadow: "0 0 25px rgba(99, 102, 241, 0.4)",
          }}>
            <ShieldAlert size={28} />
          </div>
          <h1 className="font-outfit" style={{ fontSize: "1.8rem", margin: "0 0 4px" }}>
            {isLogin ? "Welcome to NiftyMind" : "Create Your Account"}
          </h1>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0 }}>
            {isLogin ? "Analyze, secure, and grow your equity portfolio." : "Register to access SEBI-compliant risk guardrails."}
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            padding: "12px 16px",
            borderRadius: "8px",
            color: "var(--alert-error)",
            fontSize: "0.85rem",
            marginBottom: "20px",
            fontWeight: 500,
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="form-group">
              <label>Full Name</label>
              <div style={{ position: "relative" }}>
                <User size={16} color="var(--text-secondary)" style={{ position: "absolute", left: "14px", top: "14px" }} />
                <input 
                  type="text" 
                  placeholder="John Doe" 
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  style={{ paddingLeft: "42px" }}
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <div style={{ position: "relative" }}>
              <Mail size={16} color="var(--text-secondary)" style={{ position: "absolute", left: "14px", top: "14px" }} />
              <input 
                type="email" 
                placeholder="you@example.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ paddingLeft: "42px" }}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: "25px" }}>
            <label>Password</label>
            <div style={{ position: "relative" }}>
              <Lock size={16} color="var(--text-secondary)" style={{ position: "absolute", left: "14px", top: "14px" }} />
              <input 
                type="password" 
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ paddingLeft: "42px" }}
              />
            </div>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={loading}
            style={{ width: "100%", padding: "14px" }}
          >
            {loading ? "Processing..." : isLogin ? "Login to Dashboard" : "Create Account"}
          </button>
        </form>

        {/* Toggle Option */}
        <div style={{ textAlign: "center", marginTop: "24px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          {isLogin ? "New to NiftyMind? " : "Already have an account? "}
          <button 
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            style={{
              background: "none",
              border: "none",
              color: "var(--primary-color)",
              cursor: "pointer",
              fontWeight: 600,
              padding: 0,
              fontFamily: "inherit",
            }}
          >
            {isLogin ? "Sign Up" : "Log In"}
          </button>
        </div>

      </div>
    </div>
  );
};
export default AuthPage;
