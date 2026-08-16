# -*- coding: utf-8 -*-
"""패턴 5: 사용자 승인 — interrupt로 그래프 멈추기 (05-7).

견적 초안을 만든 뒤 그래프를 정지시키고, 사람의 결정을 받아 재개합니다.
정지 상태를 유지하려면 체크포인터가 필요합니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python approval_graph.py
"""
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    item: str       # 입력: 견적 대상
    quote: str      # draft 노드가 채운다
    decision: str   # approval 노드가 채운다 (사람의 답)
    status: str     # 마지막 노드가 채운다


def draft(state: State) -> dict:
    """견적 초안 작성 — 실무라면 AI 노드나 계산 노드가 온다."""
    return {"quote": f"{state['item']} 구축 견적: 3,200만 원 (부가세 별도)"}


def approval(state: State) -> dict:
    """사람 승인 노드 — interrupt에서 그래프가 멈춘다."""
    decision = interrupt(
        {
            "질문": "이 견적을 고객에게 발송할까요?",
            "견적": state["quote"],
            "선택지": ["승인", "반려"],
        }
    )
    return {"decision": decision}


def route_decision(state: State) -> Literal["send", "revise"]:
    if state["decision"] == "승인":
        return "send"
    return "revise"


def send(state: State) -> dict:
    return {"status": "견적서 발송 완료"}


def revise(state: State) -> dict:
    return {"status": "반려 — 견적 재작성 대기"}


builder = StateGraph(State)
builder.add_node("draft", draft)
builder.add_node("approval", approval)
builder.add_node("send", send)
builder.add_node("revise", revise)

builder.add_edge(START, "draft")
builder.add_edge("draft", "approval")
builder.add_conditional_edges("approval", route_decision, {"send": "send", "revise": "revise"})
builder.add_edge("send", END)
builder.add_edge("revise", END)

# interrupt로 멈춘 상태를 기억하려면 체크포인터가 필수다
graph = builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "quote-2026-001"}}

    print("=== 1. 실행 — 승인 지점에서 멈춘다 ===")
    result = graph.invoke({"item": "사내 문서 검색 챗봇"}, config)
    pending = result["__interrupt__"][0].value
    print(f"질문: {pending['질문']}")
    print(f"견적: {pending['견적']}")
    print(f"선택지: {pending['선택지']}")
    print()

    print("=== 2. 사람이 '승인'을 선택 — 멈춘 곳부터 재개 ===")
    result = graph.invoke(Command(resume="승인"), config)
    print(f"결정: {result['decision']} / 상태: {result['status']}")
    print()

    print("=== 3. 다른 스레드에서 '반려'를 선택하면 ===")
    config2 = {"configurable": {"thread_id": "quote-2026-002"}}
    graph.invoke({"item": "물류 관제 대시보드"}, config2)
    result = graph.invoke(Command(resume="반려"), config2)
    print(f"결정: {result['decision']} / 상태: {result['status']}")
