# -*- coding: utf-8 -*-
"""패턴 2: 병렬 실행 — 팬아웃과 취합 (05-3).

같은 세 가지 조사를 순차 그래프와 병렬 그래프로 각각 실행해
소요 시간을 비교합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python parallel_graph.py
"""
import operator
import os
import sys
import time
from typing import Annotated, TypedDict

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


class State(TypedDict):
    """findings는 여러 노드가 동시에 추가하므로 병합 규칙(리듀서)이 필요하다."""

    topic: str
    findings: Annotated[list[str], operator.add]  # 각 노드의 결과를 이어 붙인다
    merged: str


def _research(state: State, aspect: str) -> dict:
    msg = llm.invoke(
        f"'{state['topic']}'를 {aspect} 관점에서 조사해 핵심 사실 2가지를 "
        "각각 한 문장으로 쓰세요."
    )
    return {"findings": [f"[{aspect}] {msg.content}"]}


def research_market(state: State) -> dict:
    """시장 관점 조사."""
    return _research(state, "시장")


def research_tech(state: State) -> dict:
    """기술 관점 조사."""
    return _research(state, "기술")


def research_policy(state: State) -> dict:
    """규제·정책 관점 조사."""
    return _research(state, "규제")


def merge(state: State) -> dict:
    """취합 노드 — 세 조사가 전부 끝난 뒤에 실행된다."""
    return {"merged": f"조사 {len(state['findings'])}건 취합 완료"}


RESEARCHERS = ["research_market", "research_tech", "research_policy"]


def build_parallel():
    """팬아웃: START에서 세 노드로 동시에 퍼진다."""
    builder = StateGraph(State)
    for name, fn in zip(RESEARCHERS, [research_market, research_tech, research_policy]):
        builder.add_node(name, fn)
    builder.add_node("merge", merge)
    for name in RESEARCHERS:
        builder.add_edge(START, name)   # 팬아웃
        builder.add_edge(name, "merge")  # 팬인 — merge는 셋을 모두 기다린다
    builder.add_edge("merge", END)
    return builder.compile()


def build_sequential():
    """비교용: 같은 세 노드를 일렬로 잇는다."""
    builder = StateGraph(State)
    for name, fn in zip(RESEARCHERS, [research_market, research_tech, research_policy]):
        builder.add_node(name, fn)
    builder.add_node("merge", merge)
    builder.add_edge(START, RESEARCHERS[0])
    builder.add_edge(RESEARCHERS[0], RESEARCHERS[1])
    builder.add_edge(RESEARCHERS[1], RESEARCHERS[2])
    builder.add_edge(RESEARCHERS[2], "merge")
    builder.add_edge("merge", END)
    return builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    topic = "중소기업의 생성형 AI 도입"

    seq = build_sequential()
    t0 = time.perf_counter()
    r1 = seq.invoke({"topic": topic})
    seq_s = time.perf_counter() - t0

    par = build_parallel()
    t0 = time.perf_counter()
    r2 = par.invoke({"topic": topic})
    par_s = time.perf_counter() - t0

    print(f"순차 실행: {seq_s:.2f}초 / 조사 {len(r1['findings'])}건")
    print(f"병렬 실행: {par_s:.2f}초 / 조사 {len(r2['findings'])}건")
    print(f"단축 배율: {seq_s / par_s:.2f}배")
    print()
    print("== 병렬 실행이 취합한 findings 머리글 ==")
    for finding in r2["findings"]:
        print("-", finding.split("\n")[0][:60])
    return 0


if __name__ == "__main__":
    sys.exit(main())
