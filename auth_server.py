import os
import sys
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import UPSTOX_CLIENT_ID, UPSTOX_CLIENT_SECRET

app = Flask(__name__)

REDIRECT_URI = "http://localhost:5000/callback"


@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code provided.", 400
        
    url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "code": code,
        "client_id": UPSTOX_CLIENT_ID,
        "client_secret": UPSTOX_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        token = resp_json.get("access_token")
        if not token:
            return f"Error: No access token found in response. Response: {resp_json}", 400
            
        with open("token.txt", "w") as f:
            f.write(token)
            
        return "Authorization successful! Token has been saved to token.txt. You can close this window now."
    except Exception as e:
        return f"Error during token exchange: {str(e)}", 500


def load_token(path: str = "token.txt") -> str:
    """
    Reads and returns token from file, raises FileNotFoundError 
    with helpful message if missing
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Token file '{path}' not found. Please authenticate by running "
            "auth_server.py to generate and save the token."
        )
        
    with open(path, "r") as f:
        token = f.read().strip()
        if not token:
            raise FileNotFoundError(
                f"Token file '{path}' is empty. Please run auth_server.py to re-authenticate."
            )
        return token


from urllib.parse import quote

def attempt_silent_login() -> bool:
    """
    Attempts silent (automatic) login using Upstox credentials and TOTP secret.
    Saves token to token.txt and returns True if successful, False otherwise.
    """
    username = os.getenv("UPSTOX_USERNAME")
    password = os.getenv("UPSTOX_PASSWORD")
    pin_code = os.getenv("UPSTOX_PIN_CODE")
    totp_secret = os.getenv("UPSTOX_TOTP_SECRET")
    
    client_id = UPSTOX_CLIENT_ID or os.getenv("UPSTOX_CLIENT_ID")
    client_secret = UPSTOX_CLIENT_SECRET or os.getenv("UPSTOX_CLIENT_SECRET")
    
    if all([username, password, pin_code, totp_secret, client_id, client_secret]):
        print("Automatic credentials found. Attempting silent authentication...")
        try:
            from upstox_totp import UpstoxTOTP
            
            client = UpstoxTOTP(
                username=username,
                password=password,
                pin_code=pin_code,
                totp_secret=totp_secret,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=REDIRECT_URI
            )
            
            response = client.app_token.get_access_token()
            if response.success and response.data and response.data.access_token:
                token = response.data.access_token
                with open("token.txt", "w") as f:
                    f.write(token)
                print("🎉 Silent authentication successful! Token has been saved to token.txt.")
                return True
            else:
                error_msg = response.error if response.error else "Unknown error"
                print(f"❌ Silent authentication failed: {error_msg}")
        except Exception as e:
            print(f"❌ Error during silent authentication: {e}")
            print("Falling back to manual authorization...")
    return False


if __name__ == '__main__':
    if attempt_silent_login():
        sys.exit(0)
        
    encoded_redirect_uri = quote(REDIRECT_URI, safe='')
    auth_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code&client_id={UPSTOX_CLIENT_ID}&redirect_uri={encoded_redirect_uri}"
    )
    print("\n" + "=" * 80)
    print("UPSTOX AUTHENTICATION SERVER")
    print("Visit the following link to authenticate:")
    print(auth_url)
    print("=" * 80 + "\n")
    
    app.run(port=5000, host="0.0.0.0")
