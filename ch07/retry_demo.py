# -*- coding: utf-8 -*-
"""재시도 정책과 안전 정지 (07-2).

두 번 실패하고 세 번째에 성공하는 노드로 재시도 정책을 실험하고,
예산 한도를 넘으면 스스로 멈추는 안전 정지를 만듭니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python retry_demo.py
"""
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

# ── 1. 두 번 실패하고 세 번째에 성공하는 불안정한 노드 ─────────
call_count = {"n": 0}


class State(TypedDict):
    data: str


def flaky_fetch(state: State) -> dict:
    """일시적 네트워크 오류를 흉내 낸다 — 3번째 시도에 성공."""
    call_count["n"] += 1
    print(f"  flaky_fetch 시도 {call_count['n']}회차", end=" → ")
    if call_count["n"] < 3:
        print("ConnectionError")
        raise ConnectionError("일시적 연결 실패")
    print("성공")
    return {"data": "가져온 데이터"}


def build_flaky(retry: RetryPolicy | None):
    builder = StateGraph(State)
    builder.add_node("fetch", flaky_fetch, retry_policy=retry)
    builder.add_edge(START, "fetch")
    builder.add_edge("fetch", END)
    return builder.compile()


# ── 2. 예산 안전 정지: 지출이 한도를 넘으면 멈춘다 ──────────────
BUDGET_LIMIT = 0.5  # 달러


class BudgetState(TypedDict):
    spent: float
    done: int


def costly_work(state: BudgetState) -> dict:
    """호출마다 $0.22를 쓰는 작업 노드라고 가정."""
    return {"spent": state["spent"] + 0.22, "done": state["done"] + 1}


def route_budget(state: BudgetState) -> Literal["costly_work", "safe_stop"]:
    if state["spent"] >= BUDGET_LIMIT:
        return "safe_stop"
    return "costly_work"


def safe_stop(state: BudgetState) -> dict:
    return {}


if __name__ == "__main__":
    print("=== 1. 재시도 정책 없음 ===")
    call_count["n"] = 0
    try:
        build_flaky(None).invoke({"data": ""})
    except ConnectionError as e:
        print(f"그래프 사망: ConnectionError: {e}")
    print()

    print("=== 2. RetryPolicy(max_attempts=3) ===")
    call_count["n"] = 0
    retry = RetryPolicy(max_attempts=3, initial_interval=0.5, backoff_factor=2.0)
    result = build_flaky(retry).invoke({"data": ""})
    print(f"최종 결과: {result['data']} (그래프는 죽지 않았다)")
    print()

    print("=== 3. retry_on으로 선별 재시도 ===")
    call_count["n"] = 0
    only_conn = RetryPolicy(max_attempts=3, initial_interval=0.5, retry_on=ConnectionError)
    result = build_flaky(only_conn).invoke({"data": ""})
    print(f"ConnectionError만 재시도: {result['data']}")
    print("(ValueError 같은 코드 버그였다면 재시도 없이 즉시 죽는다 — 그게 맞다)")
    print()

    print(f"=== 4. 예산 안전 정지 (한도 ${BUDGET_LIMIT}) ===")
    builder = StateGraph(BudgetState)
    builder.add_node("costly_work", costly_work)
    builder.add_node("safe_stop", safe_stop)
    builder.add_edge(START, "costly_work")
    builder.add_conditional_edges(
        "costly_work", route_budget, {"costly_work": "costly_work", "safe_stop": "safe_stop"}
    )
    builder.add_edge("safe_stop", END)
    graph = builder.compile()
    result = graph.invoke({"spent": 0.0, "done": 0})
    print(f"작업 {result['done']}회 수행, 누적 ${result['spent']:.2f}에서 안전 정지")
