from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dateutil.parser import isoparse
from decimal import Decimal

from CoinbaseService.CoinbaseService import CoinbaseService
from CoinbaseService.cb_hmac       import get_hmac_credentials
from db                             import get_session
from models.transactions            import Transaction, TxType
from models.account_sync            import AccountSync

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
    for a in assets:
        total += a.balance * svc.get_price(a.currency)
    return PortfolioOut(net_value=total, assets=assets)

@router.post("/transactions/update")
def list_txns(
    svc: CoinbaseService = Depends(get_coinbase_service),
    db: Session = Depends(get_session)
):
    inserted = 0 
    for acct in svc.get_all_accounts():
        sync  = db.get(AccountSync, acct.id)
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
                tx_type  = TxType(tx["type"]),
                tx_time  = tx_time,
            )
            db.add(orm_tx)
            try:
                db.flush()
                inserted += 1
            except IntegrityError:
                db.rollback()

        newest_time = new_txs[-1][0]
        if sync:
            sync.last_tx_time = newest_time
        else:
            db.add(AccountSync(
                account_id   = acct.id,
                last_tx_time = newest_time
            ))
        db.commit()
    return inserted
if __name__ == '__main__':
    print(list_txns())
"""
I want to have a record of recent transactions, which requires querying over all active accounts for probably like top 5 recent transactions and then displaying those and formatting them. 
I want to display unrealized and realized P&L. This gets tricky, for realized P&L,I need to do a FIFO matching with the sell tx (price * quantity) and look at the first tx I had with that asset and find the difference. This means I need to store every transaction in the database. Lowk on some orderbook vibes with the fifo. 
I want to also have a metric for average entry price which also requires querying all transactions on an asset. This must be updated when I sell (or not?).
Everytime the function is called, it runs the whole algorithm (for all assets check tx). This can be optimized by checking if last_tx_id == most recent tx id and skipping the asset if so. If a new asset shows up, some sqlalchemy syntax will probably be able to check if the asset is in account_sync table. Don't need to check for selling more than i have but do need to always check for if i need to update or remove an entry. (I.E. I sell my whole supply of BTC, I should probably just delete the account_sync entry from it).
"""
