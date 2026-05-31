from unittest.mock import patch, MagicMock
from notifier import send_telegram

@patch("requests.post")
def test_telegram_sends_correct_url(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    
    send_telegram(
        bot_token="TEST_BOT_TOKEN",
        chat_id="TEST_CHAT_ID",
        symbol="RELIANCE",
        spot=1000.0,
        cur_fut=980.0,
        nxt_fut=981.0,
        basis=2.0,
        spread=0.1,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    
    # Verify URL contains bot token
    called_url = mock_post.call_args[0][0]
    assert "TEST_BOT_TOKEN" in called_url
    assert "https://api.telegram.org/botTEST_BOT_TOKEN/sendMessage" == called_url


@patch("requests.post")
def test_telegram_message_contains_symbol(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    
    send_telegram(
        bot_token="TEST_BOT_TOKEN",
        chat_id="TEST_CHAT_ID",
        symbol="TCS",
        spot=1000.0,
        cur_fut=980.0,
        nxt_fut=981.0,
        basis=2.0,
        spread=0.1,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    
    # Verify post JSON payload contains symbol TCS
    called_payload = mock_post.call_args[1]["json"]
    assert "TCS" in called_payload["text"]


@patch("requests.post")
def test_telegram_called_once(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    
    send_telegram(
        bot_token="TEST_BOT_TOKEN",
        chat_id="TEST_CHAT_ID",
        symbol="INFY",
        spot=1000.0,
        cur_fut=980.0,
        nxt_fut=981.0,
        basis=2.0,
        spread=0.1,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    
    mock_post.assert_called_once()


@patch("requests.post")
def test_broadcast_telegram_removes_blocked_user(mock_post, tmp_path):
    import requests
    from notifier import broadcast_telegram
    from logger import init_db, register_telegram_user, get_registered_users
    
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    # Register two users
    register_telegram_user(db_path, "user_ok", "ok_username")
    register_telegram_user(db_path, "user_blocked", "blocked_username")
    
    # Mock post behavior:
    # First post (to user_ok) succeeds.
    # Second post (to user_blocked) raises 403 Forbidden HTTPError.
    response_ok = MagicMock(status_code=200)
    
    response_blocked = MagicMock(status_code=403)
    response_blocked.json.return_value = {"description": "Forbidden: bot was blocked by the user"}
    exception_blocked = requests.HTTPError(response=response_blocked)
    
    mock_post.side_effect = [response_ok, exception_blocked]
    
    broadcast_telegram(
        bot_token="TEST_BOT_TOKEN",
        chat_ids=["user_ok", "user_blocked"],
        db_path=db_path,
        symbol="TCS",
        spot=1000.0,
        cur_fut=980.0,
        nxt_fut=981.0,
        basis=2.0,
        spread=0.1,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    
    # Verify user_blocked is removed from DB, but user_ok remains
    registered = get_registered_users(db_path)
    assert "user_ok" in registered
    assert "user_blocked" not in registered

