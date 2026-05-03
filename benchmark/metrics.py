"""Text normalisation and Word Error Rate (WER) calculation."""
import re


def normalize(text: str) -> str:
    """Lowercase and strip punctuation for fair comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return " ".join(text.split())


def word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Standard WER = (S + D + I) / N using Levenshtein distance on words.
    Returns a value in [0, ∞) where 0 = perfect match.
    Capped at 1.0 for display purposes elsewhere.
    """
    ref = normalize(reference).split()
    hyp = normalize(hypothesis).split()
    if not ref:
        return 0.0

    # Space-optimised DP (only two rows)
    prev = list(range(len(hyp) + 1))
    for i, rw in enumerate(ref):
        curr = [i + 1] + [0] * len(hyp)
        for j, hw in enumerate(hyp):
            if rw == hw:
                curr[j + 1] = prev[j]
            else:
                curr[j + 1] = 1 + min(prev[j], prev[j + 1], curr[j])
        prev = curr

    return prev[len(hyp)] / len(ref)
