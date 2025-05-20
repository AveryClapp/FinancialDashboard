from CoinbaseService.CoinbaseService import CoinbaseService
from dataclasses import dataclass
from decimal import Decimal
from typing import List
from CoinbaseService.cb_hmac import get_hmac_credentials
from db import get_session

@dataclass
class Account:
    id: str
    balance: Decimal
    currency: str

@dataclass
class Portfolio:
    net_value: Decimal
    assets: List[Decimal]
    
    def __init__(self, service: CoinbaseService) -> "Portfolio":
        self.assets = service.get_active_accounts()
        total = Decimal("0")
        for acct in self.assets:
            price_usd = Decimal(service.get_price(acct.currency))
            total += acct.balance * price_usd
        self.net_value = total

def main():
    id, secret = get_hmac_credentials()
    coinbase = CoinbaseService(id, secret)
    portfolio = Portfolio(coinbase)

if __name__ == '__main__':
    main()


"""
I want to have a record of recent transactions, which requires querying over all active accounts for probably like top 5 recent transactions and then displaying those and formatting them. 
I want to display unrealized and realized P&L. This gets tricky, for realized P&L,I need to do a FIFO matching with the sell tx (price * quantity) and look at the first tx I had with that asset and find the difference. This means I need to store every transaction in the database. Lowk on some orderbook vibes with the fifo. 
I want to also have a metric for average entry price which also requires querying all transactions on an asset. This must be updated when I sell (or not?).
Everytime the function is called, it runs the whole algorithm (for all assets check tx). This can be optimized by checking if last_tx_id == most recent tx id and skipping the asset if so. If a new asset shows up, some sqlalchemy syntax will probably be able to check if the asset is in account_sync table. Don't need to check for selling more than i have but do need to always check for if i need to update or remove an entry. (I.E. I sell my whole supply of BTC, I should probably just delete the account_sync entry from it).
"""
