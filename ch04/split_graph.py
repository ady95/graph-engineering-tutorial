# -*- coding: utf-8 -*-
"""통짜 프롬프트를 세 개 노드로 쪼갠 그래프 (04-4 실습 2·3).

collect(AI) → verify(코드) → compose(AI)

각 노드의 계약(입력·수행 작업·출력)을 docstring에 명시했습니다.
verify는 LLM 없이 코드만으로 규칙 위반을 잡아냅니다.

준비:
    .env 에 OPENAI_API_KEY 설정
    (LANGFUSE_* 를 채우면 실행 추적도 함께 전송됩니다)

실행:
    uv run python split_graph.py
"""
import json
import os
import sys
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

ALLOWED_TYPES = {"연구", "사례", "통계"}


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    topic: str          # 입력: 보고서 주제
    facts: list[dict]   # collect 노드가 채운다
    check_report: str   # verify 노드가 채운다
    passed: bool        # verify 노드가 채운다
    report: str         # compose 노드가 채운다


def collect(state: State) -> dict:
    """[계약] 입력: topic / 작업: 핵심 사실 7개를 JSON으로 수집 / 출력: facts."""
    msg = llm.invoke(
        f"'{state['topic']}'에 대한 핵심 사실 정확히 7개를 수집하세요.\n"
        "각 사실은 40자 이내 한 문장, 근거 유형은 연구/사례/통계 중 하나.\n"
        "다음 JSON 형식으로만 답하세요. 다른 텍스트를 붙이지 마세요.\n"
        '{"facts": [{"text": "사실 한 문장", "evidence": "연구|사례|통계"}]}'
    )
    data = json.loads(msg.content.strip())
    return {"facts": data["facts"]}


def verify(state: State) -> dict:
    """[계약] 입력: facts / 작업: 개수·길이·근거 유형을 코드로 검사 / 출력: check_report, passed."""
    problems = []
    facts = state["facts"]
    if len(facts) != 7:
        problems.append(f"사실 수 위반: {len(facts)}개 (요구: 7개)")
    for i, fact in enumerate(facts, 1):
        if len(fact.get("text", "")) > 40:
            problems.append(f"{i}번 길이 위반: {len(fact['text'])}자")
        if fact.get("evidence") not in ALLOWED_TYPES:
            problems.append(f"{i}번 근거 유형 위반: {fact.get('evidence')}")

    if problems:
        return {"passed": False, "check_report": " / ".join(problems)}
    return {"passed": True, "check_report": "7개 사실, 길이, 근거 유형 모두 통과"}


def compose(state: State) -> dict:
    """[계약] 입력: facts, passed / 작업: 제목과 두 문장 요약으로 보고서 구성 / 출력: report."""
    listing = "\n".join(
        f"{i}. {f['text']} ({f['evidence']})" for i, f in enumerate(state["facts"], 1)
    )
    msg = llm.invoke(
        f"다음은 '{state['topic']}'에 대해 검증을 마친 사실 목록입니다.\n{listing}\n\n"
        "보고서 제목 한 줄과 두 문장 요약을 작성하세요.\n"
        "형식: 첫 줄 제목, 빈 줄, 요약 두 문장."
    )
    return {"report": msg.content}


builder = StateGraph(State)
builder.add_node("collect", collect)
builder.add_node("verify", verify)
builder.add_node("compose", compose)
builder.add_edge(START, "collect")
builder.add_edge("collect", "verify")
builder.add_edge("verify", "compose")
builder.add_edge("compose", END)
graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    callbacks = []
    langfuse = None
    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler

        langfuse = get_client()
        callbacks.append(CallbackHandler())

    result = graph.invoke(
        {"topic": "중소 제조기업의 AI 도입"},
        config={"callbacks": callbacks},
    )

    print("== collect가 수집한 사실 ==")
    for i, fact in enumerate(result["facts"], 1):
        print(f"{i}. {fact['text']} ({fact['evidence']}) — {len(fact['text'])}자")
    print()
    print(f"== verify(코드) 판정 ==")
    print(f"{'통과' if result['passed'] else '미달'}: {result['check_report']}")
    print()
    print("== compose가 만든 보고서 머리 ==")
    print(result["report"])

    if langfuse is not None:
        langfuse.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
