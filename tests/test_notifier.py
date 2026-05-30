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
