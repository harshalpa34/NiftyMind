import uuid
import csv
import io
import re
import logging
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
import asyncpg

from app.auth.dependencies import CurrentUser
from app.db.session import get_raw_db
from app.db.crud.portfolio import (
    create_portfolio,
    get_portfolios,
    get_portfolio,
    delete_portfolio,
    get_holdings,
    upsert_holding,
    delete_holding,
    record_transaction,
    get_transactions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["Portfolio Management"])

# ============================================================================
# Pydantic Schemas
# ============================================================================

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Portfolio name")

class PortfolioDetailResponse(BaseModel):
    portfolio: dict
    holdings: List[dict]

class HoldingCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., ge=0, description="Quantity owned")
    average_buy_price: float = Field(..., ge=0, description="Average buy price per unit")

class TransactionCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., gt=0, description="Quantity bought or sold")
    price: float = Field(..., ge=0, description="Execution price per unit")
    transaction_type: str = Field(..., description="BUY or SELL")

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def api_create_portfolio(
    portfolio: PortfolioCreate,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Create a new portfolio."""
    return await create_portfolio(conn, portfolio.name, current_user.id)

@router.get("", response_model=List[dict])
async def api_list_portfolios(
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """List all portfolios for the current user."""
    return await get_portfolios(conn, current_user.id)

@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
async def api_get_portfolio(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Retrieve details and holdings of a specific portfolio."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    holdings = await get_holdings(conn, portfolio_id)
    return {
        "portfolio": portfolio,
        "holdings": holdings
    }

@router.delete("/{portfolio_id}", status_code=status.HTTP_200_OK)
async def api_delete_portfolio(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Delete a specific portfolio."""
    deleted = await delete_portfolio(conn, portfolio_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    return {"status": "success", "message": "Portfolio deleted successfully."}

@router.post("/{portfolio_id}/holdings", response_model=dict, status_code=status.HTTP_200_OK)
async def api_upsert_holding(
    portfolio_id: uuid.UUID,
    holding: HoldingCreate,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Directly insert or update (upsert) a holding in the portfolio."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    return await upsert_holding(conn, portfolio_id, holding.symbol, holding.quantity, holding.average_buy_price)

@router.delete("/{portfolio_id}/holdings/{symbol}", status_code=status.HTTP_200_OK)
async def api_delete_holding(
    portfolio_id: uuid.UUID,
    symbol: str,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Remove a position completely from the portfolio."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    deleted = await delete_holding(conn, portfolio_id, symbol)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding for symbol '{symbol}' not found in this portfolio."
        )
    return {"status": "success", "message": f"Holding for '{symbol}' removed."}

@router.post("/{portfolio_id}/transactions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def api_record_transaction(
    portfolio_id: uuid.UUID,
    transaction: TransactionCreate,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Record a BUY/SELL transaction and update holdings accordingly."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    try:
        return await record_transaction(
            conn, 
            portfolio_id, 
            transaction.symbol, 
            transaction.quantity, 
            transaction.price, 
            transaction.transaction_type
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{portfolio_id}/transactions", response_model=List[dict])
async def api_get_transactions(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Retrieve transaction history for a portfolio."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    return await get_transactions(conn, portfolio_id)

@router.post("/{portfolio_id}/import", status_code=status.HTTP_200_OK)
async def api_import_csv_portfolio(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """Import holdings in bulk from an uploaded CSV or Excel file with flexible header detection."""
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )
    
    try:
        contents = await file.read()
        filename = (file.filename or "").lower()
        imported_count = 0

        # 1. Extract rows from Excel or CSV
        if filename.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
            try:
                import openpyxl
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Excel parsing library (openpyxl) is not installed on the server."
                )
            
            try:
                wb = openpyxl.load_workbook(filename=io.BytesIO(contents), data_only=True)
                sheet = wb.active
                if not sheet:
                    raise HTTPException(status_code=400, detail="Excel file is empty or has no active sheet.")
                raw_rows = list(sheet.iter_rows(values_only=True))
                rows = [[str(cell).strip() if cell is not None else "" for cell in r] for r in raw_rows]
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Failed to parse Excel file")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process Excel file: {str(e)}"
                )
        else:
            # Fallback to CSV
            try:
                csv_text = contents.decode("utf-8-sig")
                csv_file = io.StringIO(csv_text)
                reader = csv.reader(csv_file)
                rows = list(reader)
            except Exception as e:
                logger.exception("Failed to parse CSV file")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process CSV file: {str(e)}"
                )
            
        if not rows:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # 2. Scan rows to find a valid header row containing Symbol, Qty, and Price synonyms
        header_row_index = -1
        symbol_idx = None
        qty_idx = None
        price_idx = None
        
        for i, row in enumerate(rows):
            normalized_row = [str(cell).strip().lower().replace(" ", "").replace("_", "").replace("-", "") for cell in row]
            
            s_idx = next((idx for idx, h in enumerate(normalized_row) if h in ("symbol", "ticker", "stock", "company", "instrument", "code", "stockname", "isin", "name")), None)
            q_idx = next((idx for idx, h in enumerate(normalized_row) if h in ("quantity", "qty", "shares", "units", "volume", "qtyheld", "holding", "holdings")), None)
            p_idx = next((idx for idx, h in enumerate(normalized_row) if h in ("averageprice", "avgprice", "buyprice", "averagecost", "avgcost", "cost", "price", "averagebuyprice", "avgbuyprice", "buycost", "averagebuycost")), None)
            
            if s_idx is not None and q_idx is not None and p_idx is not None:
                header_row_index = i
                symbol_idx = s_idx
                qty_idx = q_idx
                price_idx = p_idx
                break
                
        if header_row_index == -1:
            raise HTTPException(
                status_code=400,
                detail="Could not map file columns. Ensure the file contains: "
                       "1) Ticker/Symbol (e.g. Stock Name, Ticker, ISIN), "
                       "2) Quantity (e.g. Qty, Shares), "
                       "3) Avg Price (e.g. Average buy price, Average Cost)."
            )
            
        # Wrap holdings replacement in a single database transaction block
        async with conn.transaction():
            # Clear all current holdings for this portfolio before importing the new ones
            await conn.execute("DELETE FROM holdings WHERE portfolio_id = $1", portfolio_id)

            # 3. Import holdings starting from the row after the header row
            for row in rows[header_row_index + 1:]:
                if not row or all(cell == "" for cell in row):
                    continue
                    
                if symbol_idx >= len(row) or qty_idx >= len(row) or price_idx >= len(row):
                    continue
                    
                symbol = str(row[symbol_idx]).strip().upper()
                if not symbol:
                    continue
                    
                try:
                    qty_str = re.sub(r"[^\d.]", "", str(row[qty_idx]))
                    price_str = re.sub(r"[^\d.]", "", str(row[price_idx]))
                    quantity = float(qty_str) if qty_str else 0.0
                    average_buy_price = float(price_str) if price_str else 0.0
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse quantity or price in row for symbol '{symbol}'; row skipped.")
                    continue
                    
                if quantity < 0 or average_buy_price < 0:
                    continue
                    
                await upsert_holding(conn, portfolio_id, symbol, quantity, average_buy_price)
                imported_count += 1
            
        logger.info(
            "Portfolio ingestion complete",
            extra={"portfolio_id": str(portfolio_id), "imported_count": imported_count}
        )
        return {
            "status": "success",
            "message": f"Successfully imported {imported_count} holdings.",
            "imported_count": imported_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to parse/import file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )
