# -*- coding: utf-8 -*-
"""LLM 첫 호출 (02-4).

모델이 응답하는지, 토큰이 얼마나 쓰였는지 확인합니다.
그래프를 만들기 전에 이 단계를 먼저 통과해야 합니다.

준비:
    .env 에 OPENAI_API_KEY (그리고 필요하면 OPENAI_BASE_URL) 설정

실행:
    uv run python first_call.py
"""
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

QUESTION = "그래프 엔지니어링을 두 문장으로 설명하세요."

# 공식 문서 기준 단가 (per 1M tokens) — 모델을 바꾸면 함께 고쳐야 합니다.
PRICE = {"gpt-5.6-luna": (0.20, 1.20)}


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        print(".env.example 을 .env 로 복사하고 값을 채우세요.")
        return 1

    model = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
    base_url = os.environ.get("OPENAI_BASE_URL") or None

    print(f"모델: {model}")
    print(f"엔드포인트: {'OpenAI 호환 서버 (OPENAI_BASE_URL)' if base_url else '공식 OpenAI API'}")
    print()

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,          # None 이면 공식 API 를 씁니다
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
    )

    print(f"Q: {QUESTION}")
    t0 = time.time()
    try:
        msg = llm.invoke(QUESTION)
    except Exception as e:
        print(f"\n호출 실패: {type(e).__name__}: {e}")
        print("\n확인할 것:")
        print("  - 키가 올바른가")
        print("  - 모델명이 올바른가 (OPENAI_MODEL)")
        print("  - OPENAI_BASE_URL 을 쓰는 경우 서버가 떠 있는가")
        return 1
    elapsed = time.time() - t0

    print(f"\nA: {msg.content}")
    print(f"\n소요 시간: {elapsed:.2f}초")

    usage = (msg.response_metadata or {}).get("token_usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if prompt_tokens is None:
        print("토큰 사용량이 응답에 포함되지 않았습니다.")
        return 0

    print(f"토큰: 입력 {prompt_tokens} / 출력 {completion_tokens} / 합계 {usage.get('total_tokens')}")

    if model in PRICE:
        p_in, p_out = PRICE[model]
        cost = prompt_tokens / 1_000_000 * p_in + completion_tokens / 1_000_000 * p_out
        print(f"비용: ${cost:.6f}  (1,000회 호출 시 약 ${cost * 1000:.3f})")
        print("\n단가는 바뀝니다. 공식 요금 문서를 확인하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
