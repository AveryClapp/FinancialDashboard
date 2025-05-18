from auth.hmac import get_hmac_credentials
from coinbase.wallet.client import Client

key_id, secret_id = get_hmac_credentials()
client = Client(key_id, secret_id)

def get_active_accounts():
    """
    Gets and returns the active wallets
    (assets) associated on the account
    """
def main():
    print(get_active_accounts()) 

if __name__ == '__main__':
    main()
