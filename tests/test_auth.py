import os
from unittest.mock import patch, MagicMock, mock_open
import pytest

from auth_server import attempt_silent_login

def test_attempt_silent_login_missing_env():
    # Ensure environment variables are missing
    with patch.dict(os.environ, {}, clear=True):
        with patch('auth_server.UPSTOX_CLIENT_ID', ''), \
             patch('auth_server.UPSTOX_CLIENT_SECRET', ''):
            assert attempt_silent_login() is False

@patch('upstox_totp.UpstoxTOTP')
def test_attempt_silent_login_success(mock_upstox_totp):
    # Mock return value of client.app_token.get_access_token()
    mock_client = MagicMock()
    mock_upstox_totp.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.data.access_token = "mock_access_token_123"
    mock_client.app_token.get_access_token.return_value = mock_response
    
    # Set the credentials in environment
    env_vars = {
        "UPSTOX_USERNAME": "9999999999",
        "UPSTOX_PASSWORD": "mypassword",
        "UPSTOX_PIN_CODE": "123456",
        "UPSTOX_TOTP_SECRET": "SECRETKEY"
    }
    
    m_open = mock_open()
    with patch.dict(os.environ, env_vars), \
         patch('auth_server.UPSTOX_CLIENT_ID', 'client_id_val'), \
         patch('auth_server.UPSTOX_CLIENT_SECRET', 'client_secret_val'), \
         patch('builtins.open', m_open):
         
         assert attempt_silent_login() is True
         
         # Assert UpstoxTOTP was instantiated with correct parameters
         mock_upstox_totp.assert_called_once_with(
             username="9999999999",
             password="mypassword",
             pin_code="123456",
             totp_secret="SECRETKEY",
             client_id="client_id_val",
             client_secret="client_secret_val",
             redirect_uri="http://localhost:5000/callback"
         )
         # Assert token was written
         m_open.assert_called_once_with("token.txt", "w")
         m_open().write.assert_called_once_with("mock_access_token_123")

@patch('upstox_totp.UpstoxTOTP')
def test_attempt_silent_login_failure(mock_upstox_totp):
    mock_client = MagicMock()
    mock_upstox_totp.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.success = False
    mock_response.error = "Invalid TOTP"
    mock_client.app_token.get_access_token.return_value = mock_response
    
    env_vars = {
        "UPSTOX_USERNAME": "9999999999",
        "UPSTOX_PASSWORD": "mypassword",
        "UPSTOX_PIN_CODE": "123456",
        "UPSTOX_TOTP_SECRET": "SECRETKEY"
    }
    
    with patch.dict(os.environ, env_vars), \
         patch('auth_server.UPSTOX_CLIENT_ID', 'client_id_val'), \
         patch('auth_server.UPSTOX_CLIENT_SECRET', 'client_secret_val'):
         
         assert attempt_silent_login() is False

@patch('upstox_totp.UpstoxTOTP')
def test_attempt_silent_login_exception(mock_upstox_totp):
    mock_upstox_totp.side_effect = Exception("Connection error")
    
    env_vars = {
        "UPSTOX_USERNAME": "9999999999",
        "UPSTOX_PASSWORD": "mypassword",
        "UPSTOX_PIN_CODE": "123456",
        "UPSTOX_TOTP_SECRET": "SECRETKEY"
    }
    
    with patch.dict(os.environ, env_vars), \
         patch('auth_server.UPSTOX_CLIENT_ID', 'client_id_val'), \
         patch('auth_server.UPSTOX_CLIENT_SECRET', 'client_secret_val'):
         
         assert attempt_silent_login() is False
