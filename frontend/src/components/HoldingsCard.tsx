import React from "react";
import Card from "./Card";

interface Holding {
  id: string;
  symbol: string;
  quantity: string;
  average_buy_price: string;
  current_price?: number;
  value?: number;
}

interface HoldingsCardProps {
  holdings: Holding[];
  risk: {
    concentration_risk?: any[];
  } | null;
}

export const HoldingsCard: React.FC<HoldingsCardProps> = ({ holdings, risk }) => {
  return (
    <Card title="Current Holdings">
      {holdings.length === 0 ? (
        <div className="holdings-empty-state">
          No active holdings. Upload a holdings file on the right to add a position.
        </div>
      ) : (
        <div className="holdings-table-wrapper">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Price</th>
                <th>Current Price</th>
                <th>Current Value</th>
                <th>P & L</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => {
                const qty = parseFloat(holding.quantity);
                const avgPrice = parseFloat(holding.average_buy_price);
                // Use mock price if returned by risk metrics calculation
                const matches = risk?.concentration_risk?.find(
                  (c: any) => c.symbol === holding.symbol,
                );
                const currVal = matches?.value || qty * avgPrice;
                const currPrice = matches ? currVal / qty : avgPrice;

                const investedVal = qty * avgPrice;
                const plAmt = currVal - investedVal;
                const plPct = avgPrice > 0 ? ((currPrice - avgPrice) / avgPrice) * 100 : 0;
                const plColor = plAmt >= 0 ? "var(--alert-success)" : "var(--alert-error)";

                return (
                  <tr key={holding.id}>
                    <td className="symbol-cell">
                      {holding.symbol}
                    </td>
                    <td>{qty.toFixed(2)}</td>
                    <td>₹{avgPrice.toFixed(2)}</td>
                    <td>₹{currPrice.toFixed(2)}</td>
                    <td className="value-cell">
                      ₹
                      {currVal.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td style={{ color: plColor, fontWeight: 600 }}>
                      <div>
                        {plAmt >= 0 ? "+" : ""}₹
                        {plAmt.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </div>
                      <div style={{ fontSize: "0.75rem", opacity: 0.85, marginTop: "2px" }}>
                        {plAmt >= 0 ? "+" : ""}
                        {plPct.toFixed(2)}%
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
export default HoldingsCard;
