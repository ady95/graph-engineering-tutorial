# -*- coding: utf-8 -*-
"""환경 점검 — 설치가 제대로 됐는지 한 번에 확인합니다.

실행:
    uv run python check_env.py

확인 항목
1. 파이썬 버전
2. 필수 패키지 설치 여부와 버전
3. 기준 버전과 일치하는지
4. 환경변수 설정 여부 (값은 출력하지 않습니다)
"""
import importlib.metadata as md
import os
import sys

# 이 스크립트는 "인코딩 설정이 안 된 환경"을 진단하는 도구입니다.
# 따라서 그 환경에서도 죽지 않아야 합니다. 출력 인코딩을 먼저 고정합니다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 이 책이 기준으로 삼는 버전
EXPECTED = {
    "langgraph": "1.2.10",
    "langchain": "1.3.14",
    "langchain-openai": "1.4.2",
    "langgraph-cli": "0.4.31",
    "langgraph-checkpoint-sqlite": "3.1.1",
    "langfuse": "4.14.3",
}

REQUIRED_ENV = ["OPENAI_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]

PY_MIN = (3, 10)
PY_BOOK = (3, 12)


def check_python():
    v = sys.version_info
    actual = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) < PY_MIN:
        return False, f"파이썬 {actual} — 3.10 이상이 필요합니다"
    if (v.major, v.minor) != PY_BOOK:
        return True, f"파이썬 {actual} — 동작하지만 이 책은 3.12 기준입니다"
    return True, f"파이썬 {actual}"


def check_packages():
    rows, ok = [], True
    for name, expected in EXPECTED.items():
        try:
            actual = md.version(name)
        except md.PackageNotFoundError:
            rows.append((name, expected, "미설치", "설치 필요"))
            ok = False
            continue
        if actual == expected:
            rows.append((name, expected, actual, "OK"))
        else:
            rows.append((name, expected, actual, "버전 다름"))
    return ok, rows


def check_imports():
    results = []
    try:
        from langgraph.graph import END, START, StateGraph  # noqa: F401

        results.append(("langgraph.graph", "OK"))
    except Exception as e:
        results.append(("langgraph.graph", f"실패: {e}"))
    try:
        from langchain_openai import ChatOpenAI  # noqa: F401

        results.append(("langchain_openai.ChatOpenAI", "OK"))
    except Exception as e:
        results.append(("langchain_openai.ChatOpenAI", f"실패: {e}"))
    try:
        from langfuse.langchain import CallbackHandler  # noqa: F401

        results.append(("langfuse.langchain.CallbackHandler", "OK"))
    except Exception as e:
        results.append(("langfuse.langchain.CallbackHandler", f"실패: {e}"))
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: F401

        results.append(("langgraph.checkpoint.sqlite.SqliteSaver", "OK"))
    except Exception as e:
        results.append(("langgraph.checkpoint.sqlite.SqliteSaver", f"실패: {e}"))
    return results


def check_env_vars():
    rows = []
    for key in REQUIRED_ENV:
        value = os.environ.get(key)
        if not value:
            rows.append((key, "미설정"))
        else:
            # 값은 절대 출력하지 않습니다 — 길이만 표시
            rows.append((key, f"설정됨 ({len(value)}자)"))
    return rows


def check_platform_env():
    """한국어 Windows 에서 개발 서버 기동을 막는 두 항목을 점검합니다."""
    rows, ok = [], True
    is_windows = sys.platform == "win32"

    utf8_mode = sys.flags.utf8_mode  # PYTHONUTF8=1 또는 -X utf8 이면 1
    if utf8_mode:
        rows.append(("PYTHONUTF8", "적용됨 (UTF-8 모드)", "OK"))
    elif is_windows:
        rows.append(("PYTHONUTF8", "미적용", "설정 필요 — 개발 서버가 기동하지 않습니다"))
        ok = False
    else:
        rows.append(("PYTHONUTF8", "미적용", "OK (Windows 아님 — 불필요)"))

    pypath = os.environ.get("PYTHONPATH", "")
    if not pypath:
        rows.append(("PYTHONPATH", "비어 있음", "OK"))
    else:
        entries = [p for p in pypath.split(os.pathsep) if p]
        rows.append(("PYTHONPATH", f"{len(entries)}개 경로 등록됨", "확인 필요 — 비우기를 권합니다"))
        ok = False

    encoding = sys.getdefaultencoding()
    fs_encoding = sys.getfilesystemencoding()
    rows.append(("기본 인코딩", f"{encoding} / 파일시스템 {fs_encoding}", "OK" if encoding == "utf-8" else "확인"))
    return ok, rows


def main():
    print("=" * 56)
    print(" 그래프 엔지니어링 환경 점검")
    print("=" * 56)

    # .env 에 넣은 키도 점검 대상에 포함합니다.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    ok_py, msg = check_python()
    print(f"\n[1] 파이썬\n    {msg}")

    ok_pkg, rows = check_packages()
    print("\n[2] 패키지 버전")
    print(f"    {'패키지':<30} {'기준':<10} {'설치됨':<10} 상태")
    for name, expected, actual, status in rows:
        print(f"    {name:<30} {expected:<10} {actual:<10} {status}")

    print("\n[3] 임포트 확인")
    imports = check_imports()
    for mod, status in imports:
        print(f"    {mod:<42} {status}")

    print("\n[4] 플랫폼 설정 (개발 서버 기동 조건)")
    ok_plat, plat_rows = check_platform_env()
    for name, value, status in plat_rows:
        print(f"    {name:<16} {value:<28} {status}")

    print("\n[5] 환경변수 (값은 출력하지 않습니다)")
    for key, status in check_env_vars():
        print(f"    {key:<24} {status}")

    print("\n" + "=" * 56)
    import_ok = all(s == "OK" for _, s in imports)
    if ok_py and ok_pkg and import_ok and ok_plat:
        print(" 점검 통과 — 다음 장으로 진행할 수 있습니다")
    elif ok_py and ok_pkg and import_ok:
        print(" 설치는 정상. 플랫폼 설정을 확인하세요 (02-1 참조)")
    else:
        print(" 점검 실패 — 위의 '설치 필요' / '실패' 항목을 확인하세요")
    print("=" * 56)
    return 0 if (ok_py and ok_pkg and import_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
