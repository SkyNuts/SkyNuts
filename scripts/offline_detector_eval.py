"""LLM 없이 돌릴 수 있는 탐지기 평가: 키워드 필터 vs 정규화+키워드 필터.

변형별 탐지율(=공격 차단율)과 정상 데이터 오탐률을 출력한다.
주의: 키워드 목록과 샘플 데이터를 같은 사람이 작성했으므로 표준어 탐지율은
      과대평가되어 있다. 경향(변형에 따른 하락폭)을 보는 용도로만 사용할 것.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pi_lab import dataset, defenses  # noqa: E402

DETECTORS = {
    "keyword": defenses.detect_keyword,
    "norm_keyword": defenses.detect_normalized_keyword,
}


def main():
    samples = dataset.build()
    attacks = [s for s in samples if s.is_attack and s.technique == "naive"]
    benign = [s for s in samples if not s.is_attack]

    rows = defaultdict(dict)
    for name, det in DETECTORS.items():
        groups = defaultdict(list)
        for s in attacks:
            key = s.variant if s.fmt == "none" else f"ko_plain+{s.fmt}"
            groups[key].append(det(s.injection))
        for key, hits in groups.items():
            rows[key][name] = f"{sum(hits)}/{len(hits)}"
        for kind in ("normal", "hard_negative"):
            b = [det(s.injection) for s in benign if s.technique == kind]
            rows[f"[정상] {kind} 오탐"][name] = f"{sum(b)}/{len(b)}"

    order = ["en", "ko_plain", "ko_polite", "ko_subjdrop", "ko_dialect_gs",
             "ko_dialect_jl", "ko_slang"] + [f"ko_plain+{f}" for f in dataset.FORMAT_TRANSFORMS] \
        + ["[정상] normal 오탐", "[정상] hard_negative 오탐"]
    print(f"{'변형':<26}{'keyword':>10}{'norm_keyword':>14}")
    for k in order:
        print(f"{k:<26}{rows[k]['keyword']:>10}{rows[k]['norm_keyword']:>14}")

    print("\n[미탐 사례 - norm_keyword]")
    for s in attacks:
        if not defenses.detect_normalized_keyword(s.injection):
            print(f"  {s.variant:<15}{s.fmt:<10}{s.injection[:60]!r}")
    print("\n[오탐 사례 - keyword]")
    for s in benign:
        if defenses.detect_keyword(s.injection):
            print(f"  {s.technique:<14}{s.injection}")


if __name__ == "__main__":
    main()
