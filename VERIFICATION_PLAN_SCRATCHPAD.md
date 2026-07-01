# Verification Plan Scratchpad: Portfolio Intelligence Platform

Use this scratchpad to manually verify the integration between the FastAPI backend and the Vite + React frontend. You can check off items (`[ ]` to `[x]`) as you execute them locally in your browser.

## 🛠️ Step 0: Prerequisites Check

Ensure both servers are running. (Antigravity has started them as background tasks in this environment):

- [ ] **Backend Server**: Listening on `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/api/v1/health`.
- [ ] **Frontend Server**: Access the dev server at `http://localhost:5173/`.

---

## 🔐 Step 1: User Account Registration & Authentication

We will test registration, login persistence, and logout flow.

- [ ] Open `http://localhost:5173/` in your browser. You should see the login screen.
- [ ] Click the **"Sign Up"** tab/toggle on the card to switch to the registration form.
- [ ] Fill in the signup details:
  - **Full Name**: `Manual Test Admin`
  - **Email**: `manual_test_user_v1@example.com` (use a fresh email)
  - **Password**: `Password123!`
- [ ] Click the **"Sign Up"** button.
- [ ] **Verification**: Ensure you are redirected automatically to the Dashboard page.
- [ ] **Verification**: Open your browser dev tools (F12) -> Application -> Local Storage. Verify that `niftymind_token` exists and is populated with a JWT.
- [ ] Try clicking the **"Logout"** button in the navbar.
- [ ] **Verification**: Ensure you are redirected back to the login screen and the local storage token is cleared.
- [ ] Log back in with `manual_test_user_v1@example.com` and `Password123!` to continue.

---

## 📁 Step 2: Portfolio Creation

Verify you can create a portfolio container under your user account.

- [ ] On the Dashboard page, click the **"Create Portfolio"** button or use the inline creation card.
- [ ] Enter the Portfolio Name: `Growth Portfolio`
- [ ] Click **"Create"**.
- [ ] **Verification**: Ensure `Growth Portfolio` appears in the list of portfolios on your dashboard card.

---

## 📈 Step 3: Transaction Logging (BUY / SELL)

We will log two transactions to build holdings for our risk and analysis engines.

- [ ] Click on the **`Growth Portfolio`** card/link to navigate to its details page (`http://localhost:5173/portfolio/<id>`).
- [ ] Locate the **"Log Transaction"** panel/form.
- [ ] **Log Transaction 1 (INFY)**:
  - **Stock Symbol**: `INFY`
  - **Transaction Type**: `BUY`
  - **Quantity**: `10`
  - **Price (per share)**: `1500`
  - Click **"Submit Transaction"**.
- [ ] **Verification**: Ensure `INFY` immediately displays in the **Holdings** table with quantity `10` and average price `1500.00`.
- [ ] **Log Transaction 2 (TCS)**:
  - **Stock Symbol**: `TCS`
  - **Transaction Type**: `BUY`
  - **Quantity**: `5`
  - **Price (per share)**: `3000`
  - Click **"Submit Transaction"**.
- [ ] **Verification**: Ensure `TCS` immediately displays in the **Holdings** table with quantity `5` and average price `3000.00`.

---

## ⚖️ Step 4: Risk Engine & Behavioral Guardrails Analysis

Here we check the automated computations for HHI score and guardrails.

- [ ] Look at the **Risk & Diversification** section on the Portfolio page.
- [ ] **Verify Diversification Score (HHI)**:
  - Calculated portfolio value based on mock market prices (INFY = 1850, TCS = 3900):
    - INFY value: 10 * 1850 = 18,500 INR (approx 48.7%)
    - TCS value: 5 * 3900 = 19,500 INR (approx 51.3%)
    - Total Value: 38,000 INR
    - Expected HHI Score should be approx `4996` (Moderate-to-High Concentration).
  - Verify that the HHI metric and sector weight gauge render properly.
- [ ] Look at the **Behavioral Guardrail Alerts** panel.
- [ ] **Verify Concentration Alert**:
  - Ensure the system shows an alert flag for `EXCESSIVE_CONCENTRATION`.
  - Check that the text describes that INFY or TCS represents more than 30% of your portfolio weight.

---

## 🤖 Step 5: AI Portfolio Advisor Analysis

Verify the LLM summary generation and highlights.

- [ ] On the Portfolio page, click the **"Generate AI Analysis"** or **"Analyze Portfolio"** button.
- [ ] **Verification**: Check that a loading indicator appears, followed by:
  - **AI Advisor Observations**: An explanation of your holdings and current asset allocation.
  - **Highlights**: Curated highlights or actionable suggestions from the LLM.

---

## 📝 Verification Results Summary

Once you complete the manual run, please record the outcomes below:

| Feature Tested | Expected Behavior | Actual Outcome (PASS / FAIL / CORS Error) |
| :--- | :--- | :--- |
| **Authentication** | Register user, persist token, login/logout redirect | |
| **Portfolio CRUD** | Create and list `Growth Portfolio` | |
| **Transaction Logging**| Log INFY/TCS trades, view updated holdings table | |
| **Risk Calculations** | Display total portfolio value, HHI diversification score | |
| **Behavioral Alerts** | Show `EXCESSIVE_CONCENTRATION` warning flag | |
| **AI Advisor Summary** | Generate observations panel via Gemini | |

### Comments & Discovered Issues:
*Example: No CORS errors, but layout slightly wraps on mobile.*
- 
