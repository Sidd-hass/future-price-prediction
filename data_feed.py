import logging

try:
    from upstox_client import FullMarketDataFeeder
except ImportError:
    try:
        from upstox_client import MarketDataStreamerV3 as FullMarketDataFeeder
    except ImportError:
        # Fallback dummy class if upstox is not installed or mocked in testing
        class FullMarketDataFeeder:
            def __init__(self, api_client=None, instrumentKeys=[], mode="full"):
                self.listeners = {}
            def on(self, event, listener):
                self.listeners[event] = listener
            def connect(self):
                pass
            def disconnect(self):
                pass

logger = logging.getLogger(__name__)

class PriceFeed:
    def __init__(self, access_token: str, instrument_map: dict, on_tick_callback):
        """
        instrument_map: dict of {symbol: {spot_key, cur_fut_key, nxt_fut_key}}
        """
        self.access_token = access_token
        self.instrument_map = instrument_map
        self.on_tick_callback = on_tick_callback
        
        self.prices = {}  # key -> price
        self.key_to_symbol = {}
        
        # Gather all keys to subscribe
        self.keys = []
        for symbol, info in instrument_map.items():
            s_key = info['spot_key']
            c_key = info['cur_fut_key']
            n_key = info['nxt_fut_key']
            
            self.keys.extend([s_key, c_key, n_key])
            self.key_to_symbol[s_key] = symbol
            self.key_to_symbol[c_key] = symbol
            self.key_to_symbol[n_key] = symbol

        # Set up Upstox Client Configuration
        try:
            from upstox_client import ApiClient, Configuration
            config = Configuration()
            config.access_token = access_token
            self.api_client = ApiClient(config)
        except ImportError:
            self.api_client = None

        # Initialize the streamer
        self.streamer = FullMarketDataFeeder(
            api_client=self.api_client,
            instrumentKeys=self.keys,
            mode="full"
        )
        self.streamer.on("message", self._on_message)

    def connect(self):
        """
        subscribes to Upstox WebSocket for all instrument keys
        """
        logger.info("Connecting PriceFeed WebSocket...")
        self.streamer.connect()

    def _on_message(self, message: dict):
        """
        internal handler that:
        1. Updates prices dict with incoming LTP
        2. Checks if all 3 prices available for any symbol
        3. Calls on_tick_callback(symbol, spot, cur_fut, nxt_fut) when ready
        """
        feeds = message.get("feeds", {})
        for key, feed_data in feeds.items():
            if key not in self.key_to_symbol:
                continue

            # Extract LTP (Last Traded Price) from various formats
            ltp = None
            if "ltpc" in feed_data:
                ltp = feed_data["ltpc"].get("ltp")
            elif "fullFeed" in feed_data:
                ff = feed_data["fullFeed"]
                if "marketFF" in ff:
                    ltp = ff["marketFF"].get("ltpc", {}).get("ltp")
                elif "indexFF" in ff:
                    ltp = ff["indexFF"].get("ltpc", {}).get("ltp")
            elif "firstLevelWithGreeks" in feed_data:
                ltp = feed_data["firstLevelWithGreeks"].get("ltpc", {}).get("ltp")

            if ltp is not None:
                self.prices[key] = float(ltp)
                
                # Check for all three pricing elements
                symbol = self.key_to_symbol[key]
                info = self.instrument_map[symbol]
                
                spot_val = self.prices.get(info['spot_key'])
                cur_fut_val = self.prices.get(info['cur_fut_key'])
                nxt_fut_val = self.prices.get(info['nxt_fut_key'])
                
                if spot_val is not None and cur_fut_val is not None and nxt_fut_val is not None:
                    self.on_tick_callback(symbol, spot_val, cur_fut_val, nxt_fut_val)

    def disconnect(self):
        """
        cleanly closes WebSocket connection
        """
        logger.info("Disconnecting PriceFeed WebSocket...")
        self.streamer.disconnect()
