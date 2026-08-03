#!/usr/bin/env python3
import asyncio
import os
import sqlite3
import sys
import logging

# Ensure absolute import path works
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable verbose logs for checkers to keep console clean
logging.getLogger("asyncpg").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("pinecone").setLevel(logging.WARNING)

# Color ANSI escape codes (Windows friendly)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def check_postgres(db_url: str):
    """Checks PostgreSQL Connection"""
    if not db_url:
        return "Not configured", "SKIP"
    
    # Replace the driver scheme for asyncpg compatibility if needed
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        import asyncpg
        conn = await asyncpg.connect(pg_url, timeout=5)
        await conn.execute("SELECT 1")
        await conn.close()
        return "Connected and queryable successfully", "OK"
    except ImportError:
        return "asyncpg library not installed", "WARN"
    except Exception as e:
        return f"Connection failed: {e}", "FAIL"

def check_sqlite(db_path: str):
    """Checks SQLite Connection"""
    if not db_path:
        return "Not configured", "SKIP"
    
    try:
        # Check if dir exists
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return f"Connected successfully at {db_path}", "OK"
    except Exception as e:
        return f"Connection failed: {e}", "FAIL"

def check_neo4j(uri: str, user: str, password: str):
    """Checks Neo4j Connection"""
    if not uri:
        return "Not configured", "SKIP"
    
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return "Connected and authenticated successfully", "OK"
    except ImportError:
        return "neo4j library not installed", "WARN"
    except Exception as e:
        return f"Connection failed: {e}", "FAIL"

def check_pinecone(api_key: str, index_name: str):
    """Checks Pinecone Connection"""
    if not api_key:
        return "Not configured", "SKIP"
    if not index_name:
        return "Index name not set", "WARN"
        
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        vectors = stats.get("total_vector_count", 0)
        return f"Connected successfully (Index: {index_name}, Total Vectors: {vectors})", "OK"
    except ImportError:
        return "pinecone library not installed", "WARN"
    except Exception as e:
        return f"Connection failed: {e}", "FAIL"

async def check_gemini(api_key: str, model_name: str):
    """Checks Gemini API Key and basic response"""
    if not api_key:
        return "Not configured", "SKIP"
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        # Run a quick lightweight generation request to verify key validity
        response = client.models.generate_content(
            model=model_name or "gemini-2.5-flash",
            contents="State 'OK' in one word."
        )
        ans = response.text.strip() if response.text else ""
        return f"Connected and verified key (Response: '{ans}')", "OK"
    except ImportError:
        return "google-genai library not installed", "WARN"
    except Exception as e:
        return f"Key validation failed: {e}", "FAIL"

async def run_diagnostics():
    print(f"\n{BOLD}{CYAN}==================================================")
    print("      NIFTYMIND PRE-STARTUP FLIGHT CHECKS")
    print(f"=================================================={RESET}\n")
    
    # Load configuration
    try:
        from app.config import get_settings
        settings = get_settings()
        print("OK: Configuration loaded successfully from .env")
    except Exception as e:
        print(f"{RED}[FAIL]{RESET} Failed to load settings: {e}")
        sys.exit(1)
        
    checks = [
        ("SQLite Database", lambda: asyncio.to_thread(check_sqlite, settings.db_path), True),
        ("PostgreSQL Database", lambda: check_postgres(settings.database_url), True),
        ("Neo4j Graph Database", lambda: asyncio.to_thread(check_neo4j, settings.neo4j_uri, settings.neo4j_username, settings.neo4j_password), False),
        ("Pinecone Vector Store", lambda: asyncio.to_thread(check_pinecone, settings.pinecone_api_key, settings.pinecone_index_name), False),
        ("Gemini AI API Key", lambda: check_gemini(settings.gemini_api_key, settings.model_name), True),
    ]
    
    failures = 0
    warnings = 0
    
    for name, check_func, is_critical in checks:
        print(f"Checking {BOLD}{name}{RESET}...", end="", flush=True)
        try:
            res = check_func()
            if asyncio.iscoroutine(res):
                detail, status = await res
            else:
                detail, status = res
        except Exception as e:
            detail, status = f"Check runner error: {e}", "FAIL"
            
        # If a non-critical check failed, downgrade to a warning
        if status == "FAIL" and not is_critical:
            status = "WARN"
            detail = f"(Non-Critical) {detail}"
            
        # Erase current line's print and display with status
        sys.stdout.write("\r")
        if status == "OK":
            print(f"{GREEN}[OK]{RESET} {BOLD}{name:<25}{RESET} -> {detail}")
        elif status == "SKIP":
            print(f"{BLUE}[SKIP]{RESET} {BOLD}{name:<25}{RESET} -> {detail}")
        elif status == "WARN":
            print(f"{YELLOW}[WARN]{RESET} {BOLD}{name:<25}{RESET} -> {detail}")
            warnings += 1
        else:
            print(f"{RED}[FAIL]{RESET} {BOLD}{name:<25}{RESET} -> {detail}")
            failures += 1

    print(f"\n{BOLD}{CYAN}==================================================")
    print("                  SUMMARY STATUS")
    print(f"=================================================={RESET}")
    print(f"Failures: {RED}{failures}{RESET} | Warnings: {YELLOW}{warnings}{RESET}")
    
    if failures > 0:
        print(f"\n{RED}{BOLD}[FAIL] Pre-flight checks failed! Please fix critical connection issues before starting the server.{RESET}\n")
        return False
    else:
        print(f"\n{GREEN}{BOLD}[SUCCESS] All critical connections are working fine! Ready to start.{RESET}\n")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_diagnostics())
    if not success:
        sys.exit(1)
