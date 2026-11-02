"""SQLite 결과 집계: 변형 × 방어기법별 공격 성공률(ASR), 오탐률(FPR), 평균 지연.

python -m pi_lab.report --db results.db
"""
import argparse
import sqlite3

import pandas as pd


def load(db):
    return pd.read_sql("SELECT * FROM runs", sqlite3.connect(db))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="results.db")
    p.add_argument("--csv", help="전체 응답을 CSV로 저장 (엑셀에서 열어 검수)")
    a = p.parse_args()
    df = load(a.db)
    if a.csv:
        df.to_csv(a.csv, index=False, encoding="utf-8-sig")
        print(f"CSV 저장: {a.csv}")
    df["group"] = df.apply(lambda r: r.variant if r.fmt == "none" else f"ko_plain+{r.fmt}", axis=1)

    att = df[(df.is_attack == 1) & (df["mode"] == "attack")]
    if len(att):
        print("== 공격 성공률 ASR (%) : 행=언어/형식 변형, 열=방어기법 ==")
        for model, g in att.groupby("model"):
            print(f"\n[{model}]")
            print((g.pivot_table(index="group", columns="defense", values="attack_success",
                                 aggfunc="mean") * 100).round(1).to_string())
        n_rev = int(att.needs_review.sum())
        if n_rev:
            print(f"\n※ 성공 판정 중 {n_rev}건은 거부/인용 문맥일 수 있음 → --csv로 내보내 needs_review=1 행 확인")

    ben = df[(df.is_attack == 0) & (df["mode"] == "attack")]
    if len(ben):
        print("\n== 정상 데이터 오탐률 FPR (%) ==")
        print((ben.pivot_table(index="technique", columns="defense", values="blocked",
                               aggfunc="mean") * 100).round(1).to_string())

    print("\n== 평균 지연 (초) ==")
    print(df[df["mode"] == "attack"].pivot_table(index="model", columns="defense",
                                                 values="latency", aggfunc="mean").round(2).to_string())

    probe = df[df["mode"] == "probe"]
    if len(probe):
        print("\n== 이해도(probe): 제약 없이 직접 요청 시 수행률 (%) ==")
        print((probe.pivot_table(index="group", columns="model", values="attack_success",
                                 aggfunc="mean") * 100).round(1).to_string())


if __name__ == "__main__":
    main()
