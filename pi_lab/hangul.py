"""한글 자모 분해/재결합 유틸 (외부 라이브러리 없이 구현)."""

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ",
        "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
BASE = 0xAC00


def is_syllable(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def is_hangul(ch: str) -> bool:
    return is_syllable(ch) or 0x3131 <= ord(ch) <= 0x318E


def decompose_to_compat_jamo(s: str) -> str:
    out = []
    for ch in s:
        if is_syllable(ch):
            code = ord(ch) - BASE
            out += [CHO[code // 588], JUNG[(code % 588) // 28], JONG[code % 28]]
        else:
            out.append(ch)
    return "".join(out)


def compose_compat_jamo(s: str) -> str:
    """ㅁㅜㅅㅣ → 무시. 단순 그리디 결합(겹받침 조합은 미지원)."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in CHO and i + 1 < n and s[i + 1] in JUNG:
            cho, jung = CHO.index(c), JUNG.index(s[i + 1])
            jong = 0
            if i + 2 < n and s[i + 2] in JONG[1:]:
                # 다음 글자가 모음이면 받침이 아니라 다음 음절의 초성
                if not (i + 3 < n and s[i + 3] in JUNG):
                    jong = JONG.index(s[i + 2])
            out.append(chr(BASE + cho * 588 + jung * 28 + jong))
            i += 3 if jong else 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def interleave_hangul(s: str, sep: str) -> str:
    """연속된 한글 음절 사이에 구분자를 끼워 넣는다 (무시해 → 무.시.해)."""
    out = []
    for i, ch in enumerate(s):
        out.append(ch)
        if i + 1 < len(s) and is_hangul(ch) and is_hangul(s[i + 1]):
            out.append(sep)
    return "".join(out)
