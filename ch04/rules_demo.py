# -*- coding: utf-8 -*-
"""규칙이 있는 프롬프트와 없는 프롬프트 (04-2).

같은 질문을 두 번 던집니다.
한 번은 규칙 없이, 한 번은 검증 가능한 규칙과 JSON 형식을 붙여서.
그리고 형식을 고정한 출력은 코드로 검증할 수 있음을 확인합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python rules_demo.py
"""
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,  # 비우면 공식 API
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

TOPIC = "원격근무 도입의 장점"

PROMPT_NO_RULE = f"{TOPIC}을 정리해 주세요."

PROMPT_WITH_RULE = (
    f"{TOPIC}을 정리해 주세요.\n"
    "규칙:\n"
    "1. 정확히 5개 항목\n"
    "2. 항목마다 제목은 15자 이내\n"
    "3. 항목마다 근거 유형을 연구/사례/통계 중 하나로 표시\n"
    "다음 JSON 형식으로만 답하세요. 다른 텍스트를 붙이지 마세요.\n"
    '{"items": [{"title": "제목", "evidence_type": "연구|사례|통계"}]}'
)

ALLOWED_TYPES = {"연구", "사례", "통계"}


def check_rules(data: dict) -> list[str]:
    """규칙 위반을 코드로 잡아낸다. 위반이 없으면 빈 리스트."""
    problems = []
    items = data.get("items", [])
    if len(items) != 5:
        problems.append(f"항목 수 위반: {len(items)}개 (요구: 5개)")
    for i, item in enumerate(items, 1):
        if len(item.get("title", "")) > 15:
            problems.append(f"{i}번 제목 길이 위반: {len(item['title'])}자")
        if item.get("evidence_type") not in ALLOWED_TYPES:
            problems.append(f"{i}번 근거 유형 위반: {item.get('evidence_type')}")
    return problems


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    print("=== 1. 규칙 없는 프롬프트 ===")
    msg = llm.invoke(PROMPT_NO_RULE)
    print(msg.content[:400])
    print(f"... (총 {len(msg.content)}자)")
    print()

    print("=== 2. 규칙 + JSON 형식을 붙인 프롬프트 ===")
    msg = llm.invoke(PROMPT_WITH_RULE)
    raw = msg.content.strip()
    print(raw)
    print()

    print("=== 3. 코드로 규칙 검증 ===")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e} — 이 자체가 규칙 위반 신호다")
        return 1

    problems = check_rules(data)
    if problems:
        for p in problems:
            print(f"  위반: {p}")
    else:
        print("  위반 없음 — 5개 항목, 제목 길이, 근거 유형 모두 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
