# -*- coding: utf-8 -*-
"""같은 판정을 코드와 AI로 각각 구현해 비교 (04-3).

작업: "수집된 항목이 10개 이상인가?"를 판정한다.
코드 한 줄이면 되는 일을 AI에게 시키면 무엇이 달라지는지 잰다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python three_ways.py
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

# 수집된 항목 8건 — 기준(10건)에 미달하는 상황
ITEMS = [f"수집 자료 {i}: 원격근무 관련 통계" for i in range(1, 9)]


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    print(f"수집된 항목: {len(ITEMS)}건 / 기준: 10건 이상")
    print()

    # 방식 1: 코드 — 명확한 규칙은 코드가 판정한다
    t0 = time.perf_counter()
    ok = len(ITEMS) >= 10
    code_ms = (time.perf_counter() - t0) * 1000
    print(f"[코드 판정]  결과: {'통과' if ok else '미달'}")
    print(f"             소요: {code_ms:.4f}ms / 비용: $0 / 같은 입력엔 항상 같은 답")
    print()

    # 방식 2: AI — 같은 판정을 LLM에게 시키면
    listing = "\n".join(f"- {item}" for item in ITEMS)
    t0 = time.perf_counter()
    msg = llm.invoke(
        f"다음 목록의 항목이 10개 이상이면 '통과', 미만이면 '미달'이라고만 답하세요.\n{listing}"
    )
    ai_s = time.perf_counter() - t0
    usage = (msg.response_metadata or {}).get("token_usage") or {}
    print(f"[AI 판정]    결과: {msg.content.strip()}")
    print(
        f"             소요: {ai_s:.2f}초 / 토큰: 입력 {usage.get('prompt_tokens')} "
        f"출력 {usage.get('completion_tokens')} / 실행마다 흔들릴 수 있음"
    )
    print()

    # 방식 3: 사람 — 코드로도 AI로도 정할 수 없는 판단만 사람에게
    print("[사람 판정]  '8건이지만 품질이 좋으니 이대로 진행할까?' 같은")
    print("             전략적 예외 승인이 사람의 자리다. 그래프에 사람을")
    print("             배치하는 방법(interrupt)은 05-7에서 다룬다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
