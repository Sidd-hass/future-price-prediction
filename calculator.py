def compute_basis(spot: float, cur_fut: float) -> float:
    """
    Returns float: ((spot - cur_fut) / spot) * 100
    Positive value indicates futures at a discount to spot.
    """
    if spot == 0.0:
        return 0.0
    return ((spot - cur_fut) / spot) * 100.0


def compute_spread(cur_fut: float, nxt_fut: float) -> float:
    """
    Returns float: ((nxt_fut - cur_fut) / cur_fut) * 100
    Positive value indicates next month futures is more expensive than current.
    """
    if cur_fut == 0.0:
        return 0.0
    return ((nxt_fut - cur_fut) / cur_fut) * 100.0
