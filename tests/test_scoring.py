from models.scoring import Candidate, rank_candidates


def test_rank_prefers_larger_edge():
    candidates = [
        Candidate("A", "YES", 0.70, 0.60, liquidity=20000, confidence=1.0, correlation_penalty=0),
        Candidate("B", "YES", 0.65, 0.62, liquidity=20000, confidence=1.0, correlation_penalty=0),
    ]
    assert rank_candidates(candidates)[0].market == "A"


def test_score_penalizes_redundancy():
    low_corr = Candidate("A", "YES", 0.70, 0.60, liquidity=20000, confidence=1.0, correlation_penalty=0)
    high_corr = Candidate("B", "YES", 0.70, 0.60, liquidity=20000, confidence=1.0, correlation_penalty=1)
    assert low_corr.score > high_corr.score
