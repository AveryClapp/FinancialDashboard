from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dateutil.parser import isoparse
from decimal import Decimal
from sqlalchemy import and_, func

from CoinbaseService.CoinbaseService import CoinbaseService
from CoinbaseService.cb_hmac       import get_hmac_credentials
from db                             import get_session
from models.transactions            import Transaction, BrokerType
from models.account_sync            import AccountSync
from models.lot                     import Lot
from models.gain                    import Gain

from typing import List
from pydantic import BaseModel

router = APIRouter()


class AccountOut(BaseModel):
    id: str
    balance: Decimal
    currency: str


def get_coinbase_service() -> CoinbaseService:
    key, secret = get_hmac_credentials()
    return CoinbaseService(key, secret)

@router.post("/transactions/cb_update")
def update_txns(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    inserted = 0
    all_syncs = { row.account_id: row 
        for row in db.query(AccountSync).all() }
    for acct in svc.get_all_accounts():
        sync = all_syncs.get(acct.id)     # O(1) in‐memory lookup, no SQL
        since = sync.last_tx_time if sync else None
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc) 
        raw_txs = svc.get_transactions(acct.id, limit=250)

        new_txs = []
        for tx in raw_txs:
            tx_time = isoparse(tx["created_at"])
            if not since or tx_time > since:
                new_txs.append((tx_time, tx))
        if not new_txs:
            continue

        new_txs.sort(key=lambda pair: pair[0])

        for tx_time, tx in new_txs:
            if tx["type"] == "trade" or tx["amount"]["currency"] == "USD":
                continue
            orm_tx = Transaction(
                tx_id    = tx["id"],
                asset    = tx["amount"]["currency"],
                quantity = abs(Decimal(tx["amount"]["amount"])),
                cost_usd   = actual_amt(tx),
                tx_type  = tx["type"],
                tx_time  = tx_time,
                account_id = tx["account_id"],
                broker = BrokerType.coinbase
            )

            db.add(orm_tx)
            try:
                db.flush()
                inserted += 1
            except IntegrityError:
                db.rollback()

            # Nothing to do for a buy (besides update avg_buy_price)
            if orm_tx.tx_type == "sell":
                handle_sell(orm_tx, db)
            if orm_tx.tx_type == "buy":
                handle_buy(orm_tx, db)
        newest_time = new_txs[-1][0]
        if not sync:
            sync = AccountSync(
                account_id=acct.id, 
                asset=tx["amount"]["currency"],
                last_tx_time=newest_time
            )
            db.add(sync)
            all_syncs[acct.id] = sync
        else:
            sync.last_tx_time = newest_time

    db.commit()
    return {"new_transactions": inserted}

def actual_amt(tx):
    """
    Compute actual amount of tx after fees
    """
    if tx["type"] == "buy":
        return Decimal(tx["buy"]["subtotal"]["amount"])
    elif tx["type"] == "sell":
        return Decimal(tx["sell"]["subtotal"]["amount"])
    
def handle_sell(tx, db):
    """
    Sell an asset matching a buy transaction with 
    FIFO logic. Updating database entries and P&Ls 
    accordingly.
    """
    qty_to_sell = tx.quantity
    sell_price = tx.cost_usd / tx.quantity
    profit_total = Decimal('0')

    lots = (
        db.query(Lot)
          .filter(
              and_(
                  Lot.account_id == tx.account_id,
                  Lot.asset      == tx.asset,
                  Lot.remaining  > 0
              )
          )
          .order_by(Lot.buy_time)
          .all()
    )

    for lot in lots:
        if qty_to_sell <= 0:
            break

        match_qty = min(lot.remaining, qty_to_sell)

        lot_price    = lot.cost / lot.quantity

        profit_total += (sell_price - lot_price) * match_qty
        lot.remaining -= match_qty
        if lot.remaining == 0:
            db.delete(lot)

        qty_to_sell -= match_qty

    if qty_to_sell > 0:
        raise ValueError(f"Not enough {tx.asset} to sell – {qty_to_sell} units short")

    total_gain = Gain(
        tx_id = tx.tx_id,
        asset = tx.asset,
        quantity = tx.quantity,
        proceeds = tx.cost_usd,
        profit  = profit_total,
        broker = BrokerType.coinbase,
        matched_at = datetime.now(timezone.utc)
    )

    db.add(total_gain)
    db.commit()

def handle_buy (tx, db):
    """
    Buy an asset and record it in transactions
    """
    buy_lot = Lot(
        account_id = tx.account_id,
        tx_id = tx.tx_id,
        asset = tx.asset,
        quantity = tx.quantity,
        cost = tx.cost_usd,
        remaining = tx.quantity,
        broker = BrokerType.coinbase,
        buy_time = datetime.now(timezone.utc)
    )
    db.add(buy_lot)
    db.commit()


@router.get("/average_entry/{account_id}")
def calculate_avg_entry(account_id: str, db: Session = Depends(get_session)):
    """
    Average the buy price (with weighting) of database 
    entries corresponding to the account_id
    """
    lots = (
        db.query(Lot)
          .filter(
              and_(
                  Lot.account_id == account_id,
                  Lot.remaining  > 0
              )
          )
          .all()
    )
    total_cost = Decimal("0")
    total_quantity = Decimal("0")
    for lot in lots:
        total_cost += lot.cost
        total_quantity += lot.quantity

    return total_cost / total_quantity

@router.get("/unrealized_gains")
def unrealized_gains_total(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session            = Depends(get_session),
):
    """
    Total unrealized gain across all accounts & brokers.
    """
    lots = db.query(Lot).filter(Lot.remaining > 0).all()
    total_cost = sum((l.cost / l.quantity) * l.remaining for l in lots)
    total_value = sum(svc.get_price(l.asset) * l.remaining for l in lots)
    return {
        "total_cost":      total_cost,
        "market_value":    total_value,
        "unrealized_gain": total_value - total_cost,
    }


@router.get("/unrealized_gains/by_broker/{broker}")
def unrealized_gains_by_broker(
    broker: BrokerType,
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session            = Depends(get_session),
):
    """
    Unrealized gain broken out by broker.
    """
    lots = (
        db.query(Lot)
          .filter(Lot.remaining > 0, Lot.broker == broker)
          .all()
    )
    total_cost = sum((l.cost / l.quantity) * l.remaining for l in lots)
    total_value = sum(svc.get_price(l.asset) * l.remaining for l in lots)
    return {
        "broker":          broker.value,
        "total_cost":      total_cost,
        "market_value":    total_value,
        "unrealized_gain": total_value - total_cost,
    }


@router.get("/unrealized_gains/by_account/{account_id}")
def unrealized_gains_by_account(
    account_id: str,
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session            = Depends(get_session),
):
    """
    Unrealized gain for a single account.
    """
    lots = (
        db.query(Lot)
          .filter(Lot.remaining > 0, Lot.account_id == account_id)
          .all()
    )
    total_cost = sum((l.cost / l.quantity) * l.remaining for l in lots)
    total_value = sum(svc.get_price(l.asset) * l.remaining for l in lots)
    return {
        "account_id":      account_id,
        "total_cost":      total_cost,
        "market_value":    total_value,
        "unrealized_gain": total_value - total_cost,
    }

@router.get("/realized_gains")
def realized_gains(
    db: Session = Depends(get_session)
):
    """
    Sum up *all* realized gains across brokers/accounts.
    """
    total = db.query(func.coalesce(func.sum(Gain.profit), 0)).scalar()
    return {"realized_gain": total}

@router.get("/realized_gains/by_broker/{broker}")
def broker_realized_gains( broker: BrokerType, db: Session = Depends(get_session)):
    """
    Sum realized gains filtered by broker.
    """
    total = (
        db.query(func.coalesce(func.sum(Gain.profit), 0))
          .filter(Gain.broker == broker)
          .scalar()
    )
    return {"broker": broker.value, "realized_gain": total}

@router.get("/realized_gains/by_account/{account_id}")
def get_account_realized_gains(account_id: str, db: Session = Depends(get_session)):
    """
    Sum realized gains for a single account by joining Gain → Transaction.
    """
    total = (
        db.query(func.coalesce(func.sum(Gain.profit), 0))
          .join(Transaction, Transaction.tx_id == Gain.tx_id)
          .filter(Transaction.account_id == account_id)
          .scalar()
    )
    return {"account_id": account_id, "realized_gain": total}

@router.get("/active_positions")
def get_unrealized_lots(
    limit: int = 15, 
    order: str = "desc",
    db: Session = Depends(get_session)
):
    """
    Gets active positions
    """
    if order.lower() not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'")
    
    query = db.query(Lot)
    
    if order.lower() == "desc":
        query = query.order_by(Lot.buy_time.desc())
    else:
        query = query.order_by(Lot.buy_time.asc())
    
    lots = query.limit(limit).all()
    formatted_lots = []
    for lot in lots:
        formatted_lots.append(format_lot_response(lot))
    return formatted_lots

def format_lot_response(lot_data):
    # Calculate effective cost basis (cost per unit)
    effective_cost_basis = lot.cost / lot.quantity if lot.quantity > 0 else 0
    
    # Get current price and calculate unrealized gain
    current_price = get_price(lot.asset)
    current_value = lot.remaining * Decimal(str(current_price))
    cost_of_remaining = (lot.cost / lot.quantity) * lot.remaining if lot.quantity > 0 else 0
    unrealized_gain = current_value - cost_of_remaining
    
    formatted_time = lot.buy_time.strftime("%B %d, %Y at %I:%M %p")
    
    return {
        "quantity": f"{lot.remaining:.8f}",
        "effective_cost_basis": f"{effective_cost_basis:.2f}",
        "cost_remaining": f"${cost_of_remaining:.2f}",
        "broker": lot.broker.value.title(),
        "buy_time": formatted_time,
        "unrealized_gain": f"${unrealized_gain:.2f}"
    }

@router.get("/closed_positions")
def get_realized_positions(
    limit: int = 15, 
    order: str = "desc",
    db: Session = Depends(get_session)
):
    """
    Gets active positions
    """
    if order.lower() not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'")
    
    query = db.query(Gain)
    
    if order.lower() == "desc":
        query = query.order_by(Gain.matched_at.desc())
    else:
        query = query.order_by(Gain.matched_at.asc())
    
    gains = query.limit(limit).all()
    formatted_gains = []
    for gain in gains:
       formatted_gains.append(format_gain_response(gain)) 
    return formatted_gains

def format_gain_response(gain_data):
    # Parse the datetime string and format it
    formatted_date = gain_data.matched_at.strftime("%B %d, %Y at %I:%M %p")
    
    return {
        "broker": gain_data.broker,
        "asset": gain_data.asset,
        "quantity": f"{gain_data.quantity:.8f}",
        "profit": f"${gain_data.profit:.2f}",
        "sold_at": formatted_date
    }


@router.get("/transactions/{limit}")
def get_transactions(
    limit: int = 50,
    order: str = "desc",
    db: Session = Depends(get_session)
):
    query = db.query(Transaction)
    
    if order == "desc":
        query = query.order_by(Transaction.tx_time.desc())
    else:
        query = query.order_by(Transaction.tx_time.asc())
    
    transactions = query.limit(limit).all()
    
    # Format the response
    formatted_transactions = []
    for tx in transactions:
        # Calculate price per unit
        price_per_unit = tx.cost_usd / tx.quantity if tx.quantity > 0 else 0
        
        formatted_transactions.append({
            "broker": tx.broker.value.title(),
            "asset": tx.asset,
            "transaction_type": tx.tx_type.replace('_', ' ').title(),
            "quantity": f"{tx.quantity:.8f}",
            "total_cost": f"${tx.cost_usd:.2f}",
            "price_per_unit": f"${price_per_unit:.2f}",
            "transaction_time": tx.tx_time.strftime("%B %d, %Y at %I:%M %p")
        })
    
    return formatted_transactions
