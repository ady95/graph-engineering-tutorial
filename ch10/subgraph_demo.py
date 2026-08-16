# -*- coding: utf-8 -*-
"""그래프 안의 그래프 — 서브그래프 (10-1).

조사 서브그래프(수집 → 정리)를 컴파일해 부모 그래프의 노드로 답니다.
1) 스키마가 같으면 컴파일된 그래프를 그대로 add_node
2) 스키마가 다르면 변환 함수로 감싸서 연결
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python subgraph_demo.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# ── 서브그래프: 조사팀의 내부 절차 ─────────────────────────────
class ResearchState(TypedDict):
    """조사팀 내부에서만 쓰는 스테이트."""

    topic: str
    raw_notes: str   # collect가 채움 — 팀 밖에서는 안 보임
    findings: str    # 팀의 최종 산출물


def collect(state: ResearchState) -> dict:
    return {"raw_notes": f"'{state['topic']}' 원자료 5건 수집 (중간 산출물)"}


def organize(state: ResearchState) -> dict:
    return {"findings": f"'{state['topic']}' 핵심 사실 3건 정리"}


research_builder = StateGraph(ResearchState)
research_builder.add_node("collect", collect)
research_builder.add_node("organize", organize)
research_builder.add_edge(START, "collect")
research_builder.add_edge("collect", "organize")
research_builder.add_edge("organize", END)
research_team = research_builder.compile()  # 이 완성품이 부모의 부품이 된다


# ── 방법 1: 부모와 스키마가 겹치면 그대로 노드로 ────────────────
class ParentState(TypedDict):
    topic: str
    findings: str  # 서브그래프와 겹치는 필드만 오간다
    report: str


def write_report(state: ParentState) -> dict:
    return {"report": f"[보고서] {state['findings']} 기반 작성"}


builder = StateGraph(ParentState)
builder.add_node("research_team", research_team)  # 컴파일된 그래프가 곧 노드
builder.add_node("write_report", write_report)
builder.add_edge(START, "research_team")
builder.add_edge("research_team", "write_report")
builder.add_edge("write_report", END)
graph_shared = builder.compile()


# ── 방법 2: 스키마가 다르면 변환 함수로 감싼다 ──────────────────
class OrderState(TypedDict):
    """부모의 어휘가 다르다 — 주문 언어를 쓴다."""

    product: str
    market_info: str
    decision: str


def call_research_team(state: OrderState) -> dict:
    """[변환 계약] product → topic 으로 번역해 위임, findings → market_info 로 수령."""
    result = research_team.invoke({"topic": f"{state['product']} 시장"})
    return {"market_info": result["findings"]}


def decide(state: OrderState) -> dict:
    return {"decision": f"{state['market_info']} 검토 → 출시 보류"}


builder2 = StateGraph(OrderState)
builder2.add_node("call_research_team", call_research_team)
builder2.add_node("decide", decide)
builder2.add_edge(START, "call_research_team")
builder2.add_edge("call_research_team", "decide")
builder2.add_edge("decide", END)
graph_mapped = builder2.compile()


if __name__ == "__main__":
    print("=== 방법 1: 스키마 공유 — 컴파일된 그래프를 그대로 노드로 ===")
    result = graph_shared.invoke({"topic": "재택근무 제도"})
    print(f"부모가 받은 최종 스테이트 키: {list(result.keys())}")
    print(f"report: {result['report']}")
    print("주목: 서브그래프 내부의 raw_notes는 부모 스테이트에 없다 — 격리됐다")
    print()

    print("=== 방법 2: 스키마 번역 — 변환 함수로 감싸기 ===")
    result = graph_mapped.invoke({"product": "무선 이어폰"})
    print(f"decision: {result['decision']}")
