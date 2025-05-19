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
