from coinbase.wallet.client import Client
from cb_jwt import create_jwt
from cb_hmac import get_hmac_credentials
import requests

class CoinbaseService:
    def __init__(self, api_id: str, api_secret: str):
        self._client = Client(api_id, api_secret)
        self._base_url = "https://api.coinbase.com"

    def get_active_accounts(self):
        '''
        Gets and returns active accounts user has
        '''
        path = "/v2/accounts"
        JWT_TOKEN = create_jwt("GET", path)
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        ENDPOINT_URL = self._base_url + path
        response = requests.get(ENDPOINT_URL, headers=headers).json()
        accounts = response.get("data")
        # TODO fix this idt this is working 
        active_accounts = list(filter(
            lambda acct: float(acct['balance']['amount']) != 0.0,
            accounts
        ))
        return active_accounts

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
        accounts = response.get("data")


if __name__ == '__main__':
    id, secret = get_hmac_credentials() 
    tester = CoinbaseService(
            id,
            secret
    )
    tester.get_active_accounts()
