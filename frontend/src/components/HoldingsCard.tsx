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
