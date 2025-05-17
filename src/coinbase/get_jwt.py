from coinbase import jwt_generator
from dotenv import load_dotenv
import os

load_dotenv() 

# Fetch and print
api_key = os.getenv("COINBASE_KEY_NAME")
with open("coinbase.pem", "r") as f:
    api_secret = f.read()

def main(request_method: str, request_path: str):
    jwt_uri = jwt_generator.format_jwt_uri(request_method, request_path)
    jwt_token = jwt_generator.build_rest_jwt(jwt_uri, api_key, api_secret)
    return jwt_token

if __name__ == "__main__":
    print(main("GET","/v2/accounts/"))
