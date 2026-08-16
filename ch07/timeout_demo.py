# -*- coding: utf-8 -*-
"""노드별 타임아웃과 오류 핸들러 (07-1).

느린 노드(5초 걸리는 작업)를 세 가지 방식으로 실행합니다.
1) 타임아웃 없음 — 그래프 전체가 5초를 기다린다
2) timeout=2 — 2초에 NodeTimeoutError로 끊는다 (그래프는 오류로 죽음)
3) timeout=2 + error_handler — 실패를 스테이트에 기록하고 대체 경로로 보낸다

주의: 노드 timeout은 비동기(async) 노드에서만 동작합니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python timeout_demo.py
"""
import asyncio
import time
from typing import TypedDict

from langgraph.errors import NodeTimeoutError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class State(TypedDict):
    query: str
    answer: str
    error: str


async def slow_search(state: State) -> dict:
    """느린 조사 노드 — 응답이 5초 걸리는 외부 API를 흉내 낸다."""
    await asyncio.sleep(5)
    return {"answer": f"'{state['query']}' 정식 조사 결과"}


def absorb_and_reroute(state: State) -> Command:
    """오류 핸들러 — 실패를 기록하고 대체 경로(fallback)로 보낸다."""
    return Command(
        update={"error": "조사 노드 실패 (타임아웃)"},
        goto="fallback",
    )


def fallback(state: State) -> dict:
    return {"answer": "캐시된 어제 조사 결과로 대체 (지연 사유 기록)"}


def build(timeout: float | None, use_handler: bool):
    builder = StateGraph(State)
    builder.add_node(
        "search",
        slow_search,
        timeout=timeout,
        error_handler=absorb_and_reroute if use_handler else None,
    )
    builder.add_node("fallback", fallback)
    builder.add_edge(START, "search")
    builder.add_edge("search", END)
    builder.add_edge("fallback", END)
    return builder.compile()


async def main() -> None:
    query = {"query": "경쟁사 신제품", "answer": "", "error": ""}

    print("=== 1. 타임아웃 없음 ===")
    t0 = time.perf_counter()
    result = await build(timeout=None, use_handler=False).ainvoke(query)
    print(f"{time.perf_counter() - t0:.2f}초 — {result['answer']}")
    print()

    print("=== 2. timeout=2초 ===")
    t0 = time.perf_counter()
    try:
        await build(timeout=2, use_handler=False).ainvoke(query)
    except NodeTimeoutError as e:
        print(f"{time.perf_counter() - t0:.2f}초 — NodeTimeoutError: {str(e)[:60]}")
        print("빨리 끊었지만, 그래프는 오류로 죽었다.")
    print()

    print("=== 3. timeout=2초 + error_handler ===")
    t0 = time.perf_counter()
    result = await build(timeout=2, use_handler=True).ainvoke(query)
    print(f"{time.perf_counter() - t0:.2f}초 — {result['answer']}")
    print(f"스테이트에 남은 실패 기록: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
