from coinbase.wallet.client import Client
from cb_jwt import create_jwt
from cb_hmac import get_hmac_credentials
from decimal import Decimal, getcontext, ROUND_DOWN
import requests

class CoinbaseService:
    def __init__(self, api_id: str, api_secret: str):
        self._client = Client(api_id, api_secret)
        self._base_url = "https://api.coinbase.com"

    def get_all_accounts(self):
        '''
        Gets and returns all accounts
        '''
        path = "/v2/accounts"
        JWT_TOKEN = create_jwt("GET", path)
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        ENDPOINT_URL = self._base_url + path
        response = requests.get(ENDPOINT_URL, headers=headers).json()
        accounts = response.get("data", [])
        return accounts

    def get_active_accounts(self):
        '''
        Gets and returns active accounts user has
        '''
        accounts = self.get_all_accounts()
        active_accounts = [
            acct for acct in accounts
            if Decimal(acct["balance"]["amount"]) > .0001
        ]
        return active_accounts

    def get_id(self, code: str):
        accounts = self.get_all_accounts()
        for acct in accounts:
            if acct['balance']['currency'] == code:
                return acct['id']

    def get_account(self, account_id: str):
        '''
        Returns data on a specific account id
        '''
        path = f"/v2/accounts/{account_id}"
        JWT_TOKEN = create_jwt("GET", path)
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        ENDPOINT_URL = self._base_url + path
        response = requests.get(ENDPOINT_URL, headers=headers).json()
        account = response.get("data", [])
        return account

    def get_price(self, asset: str):
        '''
        Get and return up-to-date asset price
        '''
        asset = asset.strip()
        if "-USD" not in asset:
            asset += "-USD"
        return self._client.get_spot_price(curency_pair = asset)["amount"]

    def get_transactions(self, asset: str, limit: int = 15):
        '''
        Returns <limit> most recent transactions
        '''
        account_id = self.get_id(asset)
        path = f"/v2/accounts/{account_id}/transactions"
        JWT_TOKEN = create_jwt("GET", path)
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        ENDPOINT_URL = self._base_url + path
        response = requests.get(ENDPOINT_URL, headers=headers).json()
        return response

if __name__ == '__main__':
    id, secret = get_hmac_credentials() 
    tester = CoinbaseService(
            id,
            secret
    )
    print(tester.get_transactions("GRT"))
