from dotenv import load_dotenv
import os


load_dotenv()

def get_hmac_credentials():
    key_id = os.getenv("COINBASE_KEY_ID")
    secret_id = os.getenv("COINBASE_SECRET_ID")
    return (key_id, secret_id)

if __name__ == '__main__':
    print(get_hmac_credentials())
