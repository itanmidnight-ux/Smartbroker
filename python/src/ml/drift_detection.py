def simple_drift_score(current_mean: float, baseline_mean: float) -> float:
    if baseline_mean == 0:
        return 0.0
    return abs(current_mean - baseline_mean) / abs(baseline_mean)


def should_retrain(score: float, threshold: float = 0.25) -> bool:
    return score >= threshold
