# -*- coding: utf-8 -*-
"""체크포인트와 실행 이력 조회 (06-3).

SqliteSaver를 붙여 실행하면 노드가 끝날 때마다
스테이트 스냅샷이 파일(checkpoints.sqlite)에 저장됩니다.
실행이 끝난 뒤 이력을 시간 역순으로 되짚어 봅니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python checkpoint_graph.py
"""
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    topic: str
    collected: str
    checked: str
    summary: str


def collect(state: State) -> dict:
    return {"collected": f"'{state['topic']}' 자료 3건 수집"}


def verify(state: State) -> dict:
    return {"checked": "검증 통과"}


def summarize(state: State) -> dict:
    return {"summary": f"[요약] {state['collected']} / {state['checked']}"}


builder = StateGraph(State)
builder.add_node("collect", collect)
builder.add_node("verify", verify)
builder.add_node("summarize", summarize)
builder.add_edge(START, "collect")
builder.add_edge("collect", "verify")
builder.add_edge("verify", "summarize")
builder.add_edge("summarize", END)

# 파일 기반 체크포인터 — 프로세스를 껐다 켜도 이력이 남는다
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(conn))


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "report-001"}}

    result = graph.invoke({"topic": "그래프 엔지니어링"}, config)
    print("최종 결과:", result["summary"])
    print()

    print("== 실행 이력 (최신 → 과거) ==")
    for snapshot in graph.get_state_history(config):
        step = snapshot.metadata.get("step")
        next_nodes = snapshot.next or ("끝",)
        filled = [k for k, v in snapshot.values.items() if v]
        print(f"step {step}: 다음 실행 노드 = {next_nodes} / 채워진 필드 = {filled}")
