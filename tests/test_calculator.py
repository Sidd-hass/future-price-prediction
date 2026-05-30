from calculator import compute_basis, compute_spread

def test_basis_positive():
    # spot=100, cur_fut=97 -> basis=3.0
    assert compute_basis(100.0, 97.0) == 3.0


def test_basis_zero():
    # spot=100, cur_fut=100 -> basis=0.0
    assert compute_basis(100.0, 100.0) == 0.0


def test_basis_negative():
    # spot=100, cur_fut=103 -> basis=-3.0 (premium)
    assert compute_basis(100.0, 103.0) == -3.0


def test_spread_flat():
    # cur_fut=97, nxt_fut=97.1 -> ~0.103%
    res = compute_spread(97.0, 97.1)
    assert abs(res - 0.1030927835) < 1e-6


def test_spread_zero():
    # cur_fut=100, nxt_fut=100 -> 0.0
    assert compute_spread(100.0, 100.0) == 0.0
