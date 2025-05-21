from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dateutil.parser import isoparse
from decimal import Decimal

from CoinbaseService.CoinbaseService import CoinbaseService
from CoinbaseService.cb_hmac       import get_hmac_credentials
from db                             import get_session
from models.transactions            import Transaction, BrokerType
from models.account_sync            import AccountSync

from typing import List
from pydantic import BaseModel

router = APIRouter()


class AccountOut(BaseModel):
    id: str
    balance: Decimal
    currency: str

class PortfolioOut(BaseModel):
    net_value: Decimal
    assets: List[AccountOut]


def get_coinbase_service() -> CoinbaseService:
    key, secret = get_hmac_credentials()
    return CoinbaseService(key, secret)


@router.get("/portfolio", response_model=PortfolioOut)
def read_portfolio(svc: CoinbaseService = Depends(get_coinbase_service)):
    # you can still use your @dataclass Portfolio internally, or inline:
    assets = svc.get_active_accounts()
    total = Decimal(0)
    out_accts = []
    for a in assets:
        total += a.balance * svc.get_price(a.currency)
        out_accts.append(
            AccountOut(
                id = a.id,
                balance = a.balance,
                currency = a.currency
            )
        )
    return PortfolioOut(net_value=total, assets=out_accts)

@router.post("/transactions/update")
def list_txns(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    inserted = 0
    all_syncs = { row.account_id: row 
        for row in db.query(AccountSync).all() }
    for acct in svc.get_all_accounts():
        sync = all_syncs.get(acct.id)     # O(1) in‐memory lookup, no SQL
        since = sync.last_tx_time if sync else None
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
            orm_tx = Transaction(
                tx_id    = tx["id"],
                asset    = tx["amount"]["currency"],
                quantity = Decimal(tx["amount"]["amount"]),
                cost_usd = Decimal(tx["native_amount"]["amount"]),
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

def handle_sell (svc: CoinbaseService, db):
    """
    Sell an asset matching a buy transaction with 
    FIFO logic. Updating database entries and P&Ls 
    accordingly.
    """
def handle_buy (svc: CoinbaseService, db):
    """
    Buy an asset and record it in transactions
    """
@router.get("/average_entry/{account_id}")
def calculate_avg_entry(db: Session = Depends(get_session)):
    """
    Average the buy price (with weighting) of database 
    entries corresponding to the account_id
    """
    # From the lots table 
#TODO add time horizons
@router.get("/realized_gains")
def realized_gains(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    pass

@router.get("/realized_gains/{broker}")
def broker_realized_gains(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    pass

@router.get("/realized_gains/{account_id"}
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    pass


"""
I want to display unrealized and realized P&L. This gets tricky, for realized P&L,I need to do a FIFO matching with the sell tx (price * quantity) and look at the first tx I had with that asset and find the difference. This means I need to store every transaction in the database. Lowk on some orderbook vibes with the fifo. 
I want to also have a metric for average entry price which also requires querying all transactions on an asset. This must be updated when I sell (or not?).
Everytime the function is called, it runs the whole algorithm (for all assets check tx). This can be optimized by checking if last_tx_id == most recent tx id and skipping the asset if so. If a new asset shows up, some sqlalchemy syntax will probably be able to check if the asset is in account_sync table. Don't need to check for selling more than i have but do need to always check for if i need to update or remove an entry. (I.E. I sell my whole supply of BTC, I should probably just delete the account_sync entry from it). Buys and sells are detected with account_sync and handled. 
"""
