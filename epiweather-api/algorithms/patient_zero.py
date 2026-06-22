"""Stage 0: 발원지 격자 추론 — 피셔 결합 p-value."""
from __future__ import annotations
from .common import LCG, fisher_combined_p, CHANNELS


def generate_grid(origin_id: str, seed: int = 42) -> dict:
    """
    10×10 격자에서 각 셀의 발원 후방확률 계산.
    6채널 약신호 → 피셔 결합 → 정규화.
    Farrington et al. 1996 기반 스컹크웍스 원리.
    """
    import math
    lcg = LCG(seed * 31 + sum(ord(c) for c in origin_id))

    # 실제 발원 위치 (숨김 — 추론 대상)
    o_r = 1 + int(lcg.next() * 8)
    o_c = 1 + int(lcg.next() * 8)

    cells = []
    for r in range(10):
        for c in range(10):
            d = math.sqrt((r - o_r) ** 2 + (c - o_c) ** 2)
            boost = math.exp(-d * d / 2)
            zs = [boost * (0.9 + lcg.next() * 0.7) + lcg.gauss() * 0.85
                  for _ in range(6)]
            p = fisher_combined_p(zs)
            cells.append({"r": r, "c": c, "zs": zs, "p": p})

    # 후방확률 정규화
    weights = [math.exp(max(0, -math.log(max(cell["p"], 1e-9)))) for cell in cells]
    total = sum(weights)
    for i, cell in enumerate(cells):
        cell["prob"] = weights[i] / total

    # TOP 5 후보
    cands = sorted(cells, key=lambda x: -x["prob"])[:5]
    top = cands[0]

    return {
        "origin_hint": {"r": o_r, "c": o_c},  # 정답 (평가용)
        "top": {"r": top["r"], "c": top["c"], "prob": top["prob"]},
        "candidates": [
            {"rank": i + 1, "r": c["r"], "c": c["c"], "prob": c["prob"],
             "channels": [
                 {"name": CHANNELS[j]["nm"], "icon": CHANNELS[j]["ic"],
                  "z_score": c["zs"][j], "col": CHANNELS[j]["col"]}
                 for j in range(6)
             ]}
            for i, c in enumerate(cands)
        ],
        "grid": [
            {"r": cell["r"], "c": cell["c"], "prob": cell["prob"]}
            for cell in cells
        ],
    }
