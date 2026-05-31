import pytest
from unittest.mock import patch, MagicMock
import requests
import sqlite3
from logger import init_db, get_registered_users, get_bot_offset, set_bot_offset
from telegram_bot import send_bot_message, poll_updates

@patch("requests.post")
def test_send_bot_message_success(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    
    result = send_bot_message("BOT_TOKEN", "12345", "Hello World")
    
    assert result is True
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    assert "https://api.telegram.org/botBOT_TOKEN/sendMessage" == called_url
    called_json = mock_post.call_args[1]["json"]
    assert called_json["chat_id"] == "12345"
    assert called_json["text"] == "Hello World"

@patch("requests.post")
def test_send_bot_message_failure(mock_post):
    # Simulate exception in post
    mock_post.side_effect = requests.RequestException("API error")
    
    result = send_bot_message("BOT_TOKEN", "12345", "Hello World")
    
    assert result is False

@patch("requests.get")
@patch("telegram_bot.send_bot_message")
def test_poll_updates_register_user(mock_send, mock_get, tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    # 1. Setup mock responses
    # First response for offset initialization (returns nothing)
    # Second response for actual updates
    # We raise KeyboardInterrupt or similar, or use a stop_event to stop the infinite loop.
    import threading
    stop_event = threading.Event()
    
    # Mock responses for requests.get
    mock_init = MagicMock()
    mock_init.status_code = 200
    mock_init.json.return_value = {"ok": True, "result": []}
    
    mock_update = MagicMock()
    mock_update.status_code = 200
    mock_update.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 100,
                "message": {
                    "chat": {"id": 819380939},
                    "text": "/start",
                    "from": {"username": "test_username", "first_name": "Test", "last_name": "User"}
                }
            }
        ]
    }
    
    call_count = 0
    def get_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_init
        else:
            stop_event.set()
            return mock_update
        
    mock_get.side_effect = get_side_effect

    
    # Run the polling loop
    poll_updates(db_path, "BOT_TOKEN", stop_event)
    
    # Verify user was registered in DB
    users = get_registered_users(db_path)
    assert "819380939" in users
    
    # Verify we got a greeting message
    mock_send.assert_called_once()
    args = mock_send.call_args[0]
    assert args[0] == "BOT_TOKEN"
    assert args[1] == "819380939"
    assert "Welcome" in args[2]
    
    # Verify the last offset in DB is updated to 101
    assert get_bot_offset(db_path) == 101

@patch("requests.get")
@patch("telegram_bot.send_bot_message")
def test_poll_updates_unregister_user(mock_send, mock_get, tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    # Pre-register user in DB
    from logger import register_telegram_user
    register_telegram_user(db_path, "819380939", "test_username")
    
    import threading
    stop_event = threading.Event()
    
    mock_init = MagicMock()
    mock_init.status_code = 200
    mock_init.json.return_value = {"ok": True, "result": []}
    
    mock_update = MagicMock()
    mock_update.status_code = 200
    mock_update.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 200,
                "message": {
                    "chat": {"id": 819380939},
                    "text": "/stop",
                    "from": {"username": "test_username"}
                }
            }
        ]
    }
    
    call_count = 0
    def get_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_init
        else:
            stop_event.set()
            return mock_update
    mock_get.side_effect = get_side_effect
    
    poll_updates(db_path, "BOT_TOKEN", stop_event)
    
    # Verify user was unregistered
    users = get_registered_users(db_path)
    assert "819380939" not in users
    
    # Verify goodbye message was sent
    mock_send.assert_called_once()
    assert "unsubscribed" in mock_send.call_args[0][2]
    
    # Verify offset updated
    assert get_bot_offset(db_path) == 201
