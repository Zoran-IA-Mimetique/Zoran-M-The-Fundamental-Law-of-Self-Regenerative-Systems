#!/usr/bin/env python3
""" Simple estimator for ΔMΩ from an interaction log.
Input: JSON lines file with fields: timestamp, user_text, system_text, token_probs (optional), embedding (optional), ethic_event (bool)
Output: ΔMΩ estimate and component values.
"""
import sys
import json
import math
import numpy as np
from pathlib import Path


def load_log(path):
    """Load a JSONL interaction log from disk."""
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


# entropy via token_probs or surrogate using perplexity approximation
def entropy_from_probs(probs):
    """Compute entropy from a list of probabilities."""
    return -sum(p * math.log(p + 1e-12) for p in probs)


def compute_beta(entropies, recovery_window=10):
    """Compute the resilience factor β from a sequence of entropies.

    A simple slope‑based metric: locate the maximum spike in Δentropy,
    then fit a linear slope on the recovery window following the spike.
    The negative slope (decreasing entropy) maps to a positive β in [0,1].
    """
    diffs = np.diff(entropies)
    # find index of the largest increase (perturbation)
    idx = int(np.argmax(diffs))
    end = min(len(entropies), idx + recovery_window)
    y = entropies[idx:end]
    if len(y) < 3:
        return 0.5
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    # negative slope (decreasing entropy) -> positive beta
    beta = max(0.0, min(1.0, -slope / (abs(slope) + 1e-6)))
    return beta


def compute_sci(embeddings):
    """Compute the Semantic Coherence Index (SCI) from a list of embeddings."""
    if len(embeddings) < 2:
        return 0.5
    sims = []
    for i in range(1, len(embeddings)):
        a = np.array(embeddings[i - 1])
        b = np.array(embeddings[i])
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
        sims.append(float(np.dot(a, b) / denom))
    return float(np.mean(sims))


def compute_deltaCe(logs):
    """Compute Ethical Coherence Energy ΔCₑ from log entries."""
    total = 0
    corrected = 0
    for entry in logs:
        if entry.get('ethic_event'):
            corrected += 1
        if entry.get('correction_event'):
            total += 1
    if total == 0:
        return 0.0
    return corrected / total


def compute_lambda(entropies):
    """Compute entropic dissipation λ as mean of positive Δentropy values."""
    diffs = np.diff(entropies)
    pos = diffs[diffs > 0]
    if len(pos) == 0:
        return 0.0
    return float(np.mean(pos))


def compute_deltaSm(logs):
    """Compute mimetic tension ΔSₘ as variance of system output lengths."""
    lengths = [len(e.get('system_text', '')) for e in logs]
    return float(np.var(lengths))


def main():
    if len(sys.argv) < 2:
        print('Usage: compute_deltamo.py path/to/logs.jsonl')
        sys.exit(1)
    logs = load_log(sys.argv[1])
    entropies = []
    embeddings = []
    for e in logs:
        if 'token_probs' in e:
            entropies.append(entropy_from_probs(e['token_probs']))
        else:
            entropies.append(e.get('entropy_proxy', 0.5))
        if 'embedding' in e:
            embeddings.append(e['embedding'])
    beta = compute_beta(entropies)
    sci = compute_sci(embeddings)
    deltaCe = compute_deltaCe(logs)
    lam = compute_lambda(entropies)
    deltaSm = compute_deltaSm(logs)
    phi = 1.0
    numerator = (beta * deltaCe) * (sci ** phi)
    denom = lam + abs(deltaSm)
    deltamo = numerator / (denom + 1e-12)
    out = {
        'beta': beta,
        'deltaCe': deltaCe,
        'sci': sci,
        'lambda': lam,
        'deltaSm': deltaSm,
        'phi': phi,
        'deltaMOmega': deltamo
    }
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()