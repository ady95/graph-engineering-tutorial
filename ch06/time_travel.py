# -*- coding: utf-8 -*-
"""실습: 되감아 다시 실행하기 (06-4).

LLM 두 번(조사 → 요약)을 호출하는 그래프를 한 번 완주한 뒤,
1) 이력에서 요약 직전 시점을 찾고
2) 그 시점의 스테이트를 수정해 다른 결과로 분기시키고
3) 요약 노드만 다시 실행해 전체 재실행과 비용을 비교합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python time_travel.py
"""
import os
import sqlite3
import sys
import time
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)


class State(TypedDict):
    topic: str
    research: str
    summary: str


def research(state: State) -> dict:
    msg = llm.invoke(
        f"'{state['topic']}'에 대한 핵심 사실 3가지를 각각 한 문장으로 쓰세요."
    )
    return {"research": msg.content}


def summarize(state: State) -> dict:
    msg = llm.invoke(
        f"다음 조사 결과를 한 문장으로 요약하세요.\n\n{state['research']}"
    )
    return {"summary": msg.content}


builder = StateGraph(State)
builder.add_node("research", research)
builder.add_node("summarize", summarize)
builder.add_edge(START, "research")
builder.add_edge("research", "summarize")
builder.add_edge("summarize", END)

conn = sqlite3.connect("time_travel.sqlite", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(conn))


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    config = {"configurable": {"thread_id": "travel-001"}}

    # ── 0. 기준 실행: 전체 완주 (LLM 2회) ──────────────────────
    t0 = time.perf_counter()
    result = graph.invoke({"topic": "사무실 재택근무 병행 제도"}, config)
    full_s = time.perf_counter() - t0
    print(f"[전체 실행] {full_s:.2f}초 (LLM 2회)")
    print(f"요약: {result['summary'][:80]}")
    print()

    # ── 실습 1: 이력에서 '요약 직전' 시점 찾기 ─────────────────
    before_summary = None
    for snapshot in graph.get_state_history(config):
        if snapshot.next == ("summarize",):
            before_summary = snapshot
            break
    ckpt_id = before_summary.config["configurable"]["checkpoint_id"]
    print(f"[실습 1] 요약 직전 체크포인트 발견: step {before_summary.metadata.get('step')}, id={ckpt_id[:8]}...")
    print()

    # ── 실습 2: 그 시점의 스테이트를 수정해 분기시키기 ──────────
    forked = graph.update_state(
        before_summary.config,
        {"research": "1. 재택 병행 시 사무 공간 비용이 준다.\n"
                     "2. 직원 만족도가 오른다.\n"
                     "3. 신입 온보딩은 대면이 더 효과적이라는 조사가 있다."},
    )
    result2 = graph.invoke(None, forked)  # None = 새 입력 없이 그 시점부터 재개
    print("[실습 2] 조사 결과를 손으로 고친 뒤 재개:")
    print(f"새 요약: {result2['summary'][:80]}")
    print()

    # ── 실습 3: 요약 노드만 다시 실행 (부분 재실행, LLM 1회) ────
    t0 = time.perf_counter()
    result3 = graph.invoke(None, before_summary.config)
    partial_s = time.perf_counter() - t0
    print(f"[실습 3] 요약만 재실행: {partial_s:.2f}초 (LLM 1회)")
    print(f"재실행 요약: {result3['summary'][:80]}")
    print()
    print(f"전체 재실행 {full_s:.2f}초 vs 부분 재실행 {partial_s:.2f}초 — 조사 비용은 지불하지 않았다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
