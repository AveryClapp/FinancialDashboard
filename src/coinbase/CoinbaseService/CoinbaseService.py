from coinbase.wallet.client import Client
from CoinbaseService.cb_jwt import create_jwt
from decimal import Decimal
from typing import List
from dataclasses import dataclass
import requests

@dataclass
class Account:
    id: str
    balance: Decimal
    currency: str

class CoinbaseService:
    assets: List[Account]

    def __init__(self, api_id: str, api_secret: str):
        self._client   = Client(api_id, api_secret)
        self._base_url = "https://api.coinbase.com"
        # populate self.assets right away
        self.assets = self.get_active_accounts()

    def _raw_accounts(self) -> List[dict]:
        """Internal: fetch raw list of account-dicts."""
        path = "/v2/accounts"
        token = create_jwt("GET", path)
        headers = {"Authorization": f"Bearer {token}"}
        url = self._base_url + path
        data = requests.get(url, headers=headers).json().get("data", [])
        return data

    def get_all_accounts(self) -> List[Account]:
        """
        Returns every account as an Account object.
        """
        raws: List[dict] = self._raw_accounts()
        return [
            Account(
                id = acct["id"],
                balance = Decimal(acct["balance"]["amount"]),
                currency = acct["balance"]["currency"],
            )
            for acct in raws
        ]

    def get_active_accounts(self) -> List[Account]:
        """
        Returns only those accounts whose balance > 0.0001
        """
        return [
            acct for acct in self.get_all_accounts()
            if acct.balance > Decimal("0.0001")
        ]

    def get_id(self, code: str) -> str | None:
        """
        Find the Account.id for the given currency code.
        """
        for acct in self.assets:
            if acct.currency == code:
                return acct.id
        return None

    def get_account(self, account_id: str) -> Account | None:
        """
        Fetches a single account via its API and returns it as Account.
        """
        path = f"/v2/accounts/{account_id}"
        token = create_jwt("GET", path)
        headers = {"Authorization": f"Bearer {token}"}
        url = self._base_url + path
        raw = requests.get(url, headers=headers).json().get("data")
        if not raw:
            return None
        return Account(
            id = raw["id"],
            balance = Decimal(raw["balance"]["amount"]),
            currency = raw["balance"]["currency"],
        )

    def get_price(self, asset: str) -> Decimal:
        """
        Get and return up-to-date asset price (in USD).
        """
        sym = asset.strip()
        if "-USD" not in sym:
            sym += "-USD"
        amt = self._client.get_spot_price(currency_pair=sym)["amount"]
        return Decimal(amt)

    def get_transactions(self, asset: str, limit: int = 15) -> List[dict]:
        """
        Returns <limit> most recent transactions for the given asset.
        """
        acct_id = self.get_id(asset)
        if not acct_id:
            return []
        path = f"/v2/accounts/{acct_id}/transactions"
        token = create_jwt("GET", path)
        headers = {"Authorization": f"Bearer {token}"}
        url = self._base_url + path + f"?limit={limit}"
        return requests.get(url, headers=headers).json().get("data", [])

if __name__ == "__main__":
    api_id, api_secret = get_hmac_credentials()
    svc = CoinbaseService(api_id, api_secret)
