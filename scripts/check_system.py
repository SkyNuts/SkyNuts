"""내 컴퓨터에서 실험이 가능한지 사양을 점검하고 권장 모델을 알려준다.

python scripts/check_system.py
"""
import os
import platform
import shutil
import subprocess
import sys


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def ram_gb():
    try:
        if sys.platform == "darwin":
            return int(run(["sysctl", "-n", "hw.memsize"])) / 1024**3
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo") as f:
                return int(f.readline().split()[1]) / 1024**2
        if sys.platform == "win32":
            import ctypes

            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("t", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("p", ctypes.c_ulonglong * 5)]
            m = M()
            m.l = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.t / 1024**3
    except Exception:
        pass
    return 0.0


def gpu():
    out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if out:
        name, mem = out.splitlines()[0].rsplit(",", 1)
        return f"NVIDIA {name.strip()}", float(mem) / 1024
    if sys.platform == "darwin" and platform.machine() == "arm64":
        chip = run(["sysctl", "-n", "machdep.cpu.brand_string"]) or "Apple Silicon"
        return f"{chip} (통합 메모리)", ram_gb() * 0.7   # 통합 메모리의 약 70%를 GPU가 사용 가능
    return None, 0.0


def main():
    ram = ram_gb()
    gname, vram = gpu()
    free = shutil.disk_usage(os.path.expanduser("~")).free / 1024**3
    print(f"OS        : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python    : {platform.python_version()}")
    print(f"CPU 코어  : {os.cpu_count()}")
    print(f"RAM       : {ram:.1f} GB")
    print(f"GPU       : {gname or '없음 (CPU로 실행)'}" + (f", 사용 가능 메모리 약 {vram:.1f} GB" if gname else ""))
    print(f"디스크 여유: {free:.1f} GB")
    ollama = shutil.which("ollama")
    print(f"Ollama    : {run(['ollama', '--version']) if ollama else '설치 안 됨'}")

    print("\n== 판정 ==")
    if sys.version_info < (3, 10):
        print("✗ Python 3.10 이상이 필요합니다.")
    if free < 10:
        print("✗ 디스크 여유 공간이 10GB 이상 필요합니다.")
    # GPU가 없으면 메모리가 넉넉해도 7B는 호출당 수십 초라 실험 규모상 비현실적 → 소형 모델 권장
    mem = vram if gname else min(ram, 7.9)
    if mem >= 12:
        tier = "7~8B 모델 가능 (본 실험 권장 구성)"
        models = ["qwen2.5:7b", "exaone3.5:7.8b", "llama3.1:8b"]
    elif mem >= 6:
        tier = "3B급 모델 권장 (7B는 느리거나 메모리 부족 가능)"
        models = ["qwen2.5:3b", "exaone3.5:2.4b", "llama3.2:3b"]
    elif ram >= 8:
        tier = "1~2B 소형 모델만 권장 (예비실험용)"
        models = ["qwen2.5:1.5b", "exaone3.5:2.4b", "llama3.2:1b"]
    else:
        tier = "메모리 부족: 실험이 어렵습니다 (RAM 8GB 이상 권장)"
        models = []
    print(f"- {tier}")
    if models:
        print("- 권장 모델: " + ", ".join(models))
        print("- 받기: " + " && ".join(f"ollama pull {m}" for m in models))
    print(f"- {'GPU 가속 사용' if gname else 'GPU 없음: 호출당 수 초~수십 초 소요 예상'}")


if __name__ == "__main__":
    main()
