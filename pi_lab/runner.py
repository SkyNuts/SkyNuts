"""공격 실행기: 샘플 × 방어기법 × 모델을 Ollama로 실행하고 SQLite에 저장한다.

사용 예:
  python -m pi_lab.runner --models qwen2.5:1.5b llama3.2:1b --defenses none sandwich keyword
  python -m pi_lab.runner --models qwen2.5:1.5b --limit 30          # 빠른 예비실험
  python -m pi_lab.runner --probe --models qwen2.5:1.5b             # 이해도(comprehension) 측정
"""
import argparse
import datetime as dt
import sqlite3
import time

from . import dataset, defenses
from .app import attack_succeeded, strip_think

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sample_id TEXT, seed_id TEXT, is_attack INT, goal TEXT, variant TEXT, fmt TEXT,
  technique TEXT, model TEXT, model_digest TEXT, defense TEXT, mode TEXT,
  blocked INT, response TEXT, attack_success INT, latency REAL, created_at TEXT
);
"""

OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 256}


def ollama_chat(model: str, messages: list[dict]) -> str:
    import ollama
    r = ollama.chat(model=model, messages=messages, options=OPTIONS)
    return strip_think(r["message"]["content"])


def model_digest(model: str) -> str:
    try:
        import ollama
        for m in ollama.list()["models"]:
            if m["model"] == model:
                return m["digest"][:12]
    except Exception:
        pass
    return ""


def run(models, defense_names, samples, db_path, judge_model=None, mode="attack",
        chat_fn=ollama_chat):
    con = sqlite3.connect(db_path)
    con.execute(SCHEMA)
    reg = defenses.registry(chat_fn, judge_model)
    total = len(models) * len(defense_names) * len(samples)
    done = 0
    for model in models:
        digest = model_digest(model)
        for dname in defense_names:
            detect, build_messages = reg[dname]
            for s in samples:
                t0 = time.time()
                if mode == "probe":
                    # 이해도 측정: 방어/시스템 제약 없이 주입 문장 자체를 직접 요청했을 때
                    # 모델이 그 지시를 '이해하고 수행'할 수 있는지 확인
                    blocked = 0
                    resp = chat_fn(model, [
                        {"role": "system", "content": defenses.SYSTEM_PROMPT_PROBE},
                        {"role": "user", "content": s.injection}])
                else:
                    blocked = int(detect(s.data))
                    resp = "" if blocked else chat_fn(model, build_messages(s.data))
                lat = time.time() - t0
                success = int(bool(s.is_attack) and not blocked
                              and attack_succeeded(s.goal, resp))
                con.execute(
                    "INSERT INTO runs (sample_id, seed_id, is_attack, goal, variant, fmt, technique,"
                    " model, model_digest, defense, mode, blocked, response, attack_success,"
                    " latency, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (s.id, s.seed_id, s.is_attack, s.goal, s.variant, s.fmt, s.technique,
                     model, digest, dname, mode, blocked, resp, success, lat,
                     dt.datetime.now().isoformat(timespec="seconds")))
                con.commit()
                done += 1
                print(f"[{done}/{total}] {model} {dname:<12} {s.id:<40} "
                      f"blocked={blocked} success={success} {lat:.1f}s")
            if mode == "probe":
                break  # probe는 방어기법과 무관하므로 1회만
    con.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", required=True)
    p.add_argument("--defenses", nargs="+",
                   default=["none", "sandwich", "spotlight", "keyword", "norm_keyword"])
    p.add_argument("--judge-model", help="llm_judge 방어에 쓸 모델 (대상 모델과 다르게)")
    p.add_argument("--db", default="results.db")
    p.add_argument("--limit", type=int, default=0, help="샘플 수 제한(무작위, seed 고정)")
    p.add_argument("--no-formats", action="store_true", help="형식 변형 제외")
    p.add_argument("--probe", action="store_true", help="이해도 측정 모드")
    a = p.parse_args()

    samples = dataset.build(include_formats=not a.no_formats)
    if a.probe:
        samples = [s for s in samples if s.is_attack and s.technique == "naive"]
    if a.limit:
        samples = dataset.subsample(samples, a.limit)
    run(a.models, a.defenses, samples, a.db, a.judge_model,
        mode="probe" if a.probe else "attack")


if __name__ == "__main__":
    main()
