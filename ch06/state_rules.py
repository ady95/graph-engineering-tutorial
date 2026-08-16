# -*- coding: utf-8 -*-
"""스테이트 갱신 규칙 — 덮어쓸 것인가 누적할 것인가 (06-2).

같은 필드에 두 노드가 차례로 쓸 때,
리듀서가 없으면 덮어쓰고 / 리듀서가 있으면 쌓입니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python state_rules.py
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


# ── 1. 리듀서 없음: 나중 값이 이전 값을 덮어쓴다 ─────────────────
class PlainState(TypedDict):
    logs: list[str]  # 리듀서 없음 — 갱신은 곧 교체


def step_a_plain(state: PlainState) -> dict:
    return {"logs": ["A: 자료 수집 완료"]}


def step_b_plain(state: PlainState) -> dict:
    return {"logs": ["B: 검증 완료"]}  # A의 기록은 어디로?


# ── 2. 리듀서 있음: 값이 이어 붙는다 ─────────────────────────────
class ReducedState(TypedDict):
    logs: Annotated[list[str], operator.add]  # 갱신은 곧 추가


def step_a(state: ReducedState) -> dict:
    return {"logs": ["A: 자료 수집 완료"]}


def step_b(state: ReducedState) -> dict:
    return {"logs": ["B: 검증 완료"]}


def build(state_cls, a, b):
    builder = StateGraph(state_cls)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


if __name__ == "__main__":
    print("=== 1. 리듀서 없음 (기본 동작: 덮어쓰기) ===")
    result = build(PlainState, step_a_plain, step_b_plain).invoke({"logs": []})
    print(f"최종 logs: {result['logs']}")
    print("A의 기록이 사라졌다. 오류도 없이, 조용히.")
    print()

    print("=== 2. 리듀서 있음 (operator.add: 누적) ===")
    result = build(ReducedState, step_a, step_b).invoke({"logs": []})
    print(f"최종 logs: {result['logs']}")
    print("두 노드의 기록이 모두 남았다.")
