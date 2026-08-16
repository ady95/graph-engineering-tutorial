# -*- coding: utf-8 -*-
"""가장 작은 그래프 — 노드 두 개, 엣지 세 개 (03-3).

02장에서 동작만 확인했던 그래프를 이번에는 한 줄씩 이해하며 만듭니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python graph_minimal.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    topic: str
    research: str
    summary: str


def research(state: State) -> dict:
    """조사 노드 — 지금은 자리만 잡아 둡니다. 03-4에서 진짜 LLM으로 바뀝니다."""
    return {"research": f"'{state['topic']}'에 대해 수집한 자료 3건"}


def summarize(state: State) -> dict:
    """요약 노드 — 앞 노드가 채운 research를 받아 정리합니다."""
    return {"summary": f"[요약] {state['research']}"}


builder = StateGraph(State)                  # 1. 설계도 준비 — 스테이트 스키마를 넘긴다
builder.add_node("research", research)       # 2. 노드 등록
builder.add_node("summarize", summarize)
builder.add_edge(START, "research")          # 3. 엣지 연결 — 시작점부터 끝점까지
builder.add_edge("research", "summarize")
builder.add_edge("summarize", END)
graph = builder.compile()                    # 4. 컴파일 — 실행 가능한 객체로


if __name__ == "__main__":
    result = graph.invoke({"topic": "그래프 엔지니어링"})   # 5. 실행
    for key, value in result.items():
        print(f"{key}: {value}")

    print()
    print("--- 그래프 구조 (Mermaid) ---")
    print(graph.get_graph().draw_mermaid())
