# -*- coding: utf-8 -*-
"""개발 서버 동작 확인용 최소 그래프.

LLM을 호출하지 않으므로 API 키 없이도 돌아갑니다.
02-5(개발 서버)와 02-6(Studio 화면 따라 하기)에서 사용합니다.

실행:
    uv run langgraph dev
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    topic: str
    collected: str
    summary: str


def collect(state: State) -> dict:
    """조사 노드 — 자료를 모으는 자리(여기서는 흉내만 냅니다)."""
    return {"collected": f"'{state['topic']}'에 대해 수집한 자료 3건"}


def summarize(state: State) -> dict:
    """요약 노드 — 앞 노드의 결과를 받아 정리합니다."""
    return {"summary": f"[요약] {state['collected']}"}


builder = StateGraph(State)
builder.add_node("collect", collect)
builder.add_node("summarize", summarize)
builder.add_edge(START, "collect")
builder.add_edge("collect", "summarize")
builder.add_edge("summarize", END)

graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"topic": "그래프 엔지니어링"})
    for key, value in result.items():
        print(f"{key}: {value}")
