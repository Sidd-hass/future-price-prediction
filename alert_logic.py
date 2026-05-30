from datetime import datetime, timedelta

class AlertEngine:
    def __init__(self, config):
        self.basis_threshold = config.BASIS_THRESHOLD
        self.spread_min = config.SPREAD_MIN
        self.spread_max = config.SPREAD_MAX
        self.breach_count_threshold = config.BREACH_COUNT_THRESHOLD
        self.cooldown_minutes = config.COOLDOWN_MINUTES
        
        self.breach_counter = {symbol: 0 for symbol in config.WATCHLIST}
        self.last_alert_time = {}

    def check_conditions(self, basis: float, spread: float) -> bool:
        """
        Returns True if basis > BASIS_THRESHOLD
        AND SPREAD_MIN <= spread <= SPREAD_MAX
        """
        return basis > self.basis_threshold and self.spread_min <= abs(spread) <= self.spread_max

    def noise_filter(self, symbol: str, basis: float, spread: float) -> bool:
        """
        Increments breach_counter[symbol] when check_conditions is True,
        resets to 0 otherwise.
        Returns True only when counter reaches BREACH_COUNT_THRESHOLD.
        """
        if self.check_conditions(basis, spread):
            self.breach_counter[symbol] = self.breach_counter.get(symbol, 0) + 1
        else:
            self.breach_counter[symbol] = 0
            
        return self.breach_counter[symbol] == self.breach_count_threshold

    def is_cooldown_active(self, symbol: str) -> bool:
        """
        Returns True if time since last alert < COOLDOWN_MINUTES
        """
        if symbol not in self.last_alert_time:
            return False
        elapsed = datetime.now() - self.last_alert_time[symbol]
        return elapsed < timedelta(minutes=self.cooldown_minutes)

    def record_alert(self, symbol: str):
        """
        Saves datetime.now() to last_alert_time
        """
        self.last_alert_time[symbol] = datetime.now()

    def reset_breach(self, symbol: str):
        """
        Sets breach_counter[symbol] = 0
        """
        self.breach_counter[symbol] = 0

    def should_alert(self, symbol: str, basis: float, spread: float) -> bool:
        """
        Combines noise_filter and is_cooldown_active:
        Returns True only if noise filter passes AND cooldown is not active
        """
        passed_filter = self.noise_filter(symbol, basis, spread)
        cooldown_active = self.is_cooldown_active(symbol)
        return passed_filter and not cooldown_active
