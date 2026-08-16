# -*- coding: utf-8 -*-
"""상한이 없을 때 벌어지는 일 (05-6).

절대 통과하지 못하는 평가자를 두고 두 번 실행합니다.
1) 재시도 상한 없음 — LangGraph의 재귀 한도에 걸려 오류로 죽는다
2) 재시도 상한 3회 — 상한에서 멈추고 사람에게 넘긴다

LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python loop_runaway.py
"""
from typing import Literal, TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

MAX_ATTEMPTS = 3


class State(TypedDict):
    draft: str
    attempts: int


def maker(state: State) -> dict:
    attempts = state.get("attempts", 0) + 1
    return {"draft": f"초안 v{attempts}", "attempts": attempts}


def checker(state: State) -> dict:
    """일부러 항상 반려하는 평가자 — 기준을 잘못 잡으면 실제로 벌어지는 일이다."""
    return {}


def route_no_cap(state: State) -> Literal["maker"]:
    """상한 없음 — 반려면 무조건 되돌린다."""
    return "maker"


def route_with_cap(state: State) -> Literal["maker", "escalate"]:
    """상한 있음 — 재시도 횟수를 보고 멈춘다."""
    if state["attempts"] >= MAX_ATTEMPTS:
        return "escalate"
    return "maker"


def escalate(state: State) -> dict:
    return {"draft": f"{state['draft']} — 상한 도달, 사람 검토로"}


def build(route_fn, with_escalate: bool):
    builder = StateGraph(State)
    builder.add_node("maker", maker)
    builder.add_node("checker", checker)
    if with_escalate:
        builder.add_node("escalate", escalate)
        builder.add_edge("escalate", END)
        mapping = {"maker": "maker", "escalate": "escalate"}
    else:
        mapping = {"maker": "maker"}
    builder.add_edge(START, "maker")
    builder.add_edge("maker", "checker")
    builder.add_conditional_edges("checker", route_fn, mapping)
    return builder.compile()


if __name__ == "__main__":
    print("=== 1. 재시도 상한 없음 ===")
    no_cap = build(route_no_cap, with_escalate=False)
    try:
        no_cap.invoke({"draft": "", "attempts": 0})
    except GraphRecursionError as e:
        print(f"GraphRecursionError 발생: {str(e)[:80]} ...")
        print("LangGraph의 재귀 한도가 최후의 안전망으로 작동했다.")
        print("이 버전(v1.2.10)의 기본 한도는 10007단계다 — 노드가 LLM이었다면")
        print("오류로 죽기 전에 수천 번을 호출하며 비용을 태웠을 것이다.")
        print("게다가 이것은 오류로 죽는 것이지 통제된 종료가 아니다.")
    print()

    print("=== 2. 재시도 상한 3회 ===")
    with_cap = build(route_with_cap, with_escalate=True)
    result = with_cap.invoke({"draft": "", "attempts": 0})
    print(f"결과: {result['draft']}")
    print("같은 무한 반려 상황이지만, 이번에는 설계된 경로로 조용히 빠져나왔다.")
