# -*- coding: utf-8 -*-
"""패턴 1: 라우터 — 조건 분기와 Fallback (05-1, 05-2).

분류 노드가 문의 유형을 판단하면, 조건부 엣지가 담당 노드로 보냅니다.
어떤 분류에도 걸리지 않는 입력은 Fallback 경로로 흘러야 합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python router_graph.py
"""
import os
import sys
from typing import Literal, TypedDict

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

KNOWN_CATEGORIES = {"버그신고", "기능요청", "결제문의"}


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    inquiry: str    # 입력: 고객 문의 원문
    category: str   # classify 노드가 채운다
    answer: str     # 담당 노드가 채운다


def classify(state: State) -> dict:
    """분류 노드 — 문의 유형을 세 가지 중 하나로 판단한다."""
    msg = llm.invoke(
        "다음 고객 문의를 버그신고/기능요청/결제문의 중 하나로 분류하세요.\n"
        "확신이 없으면 '기타'라고 답하세요. 해당 단어 하나만 답하세요.\n"
        f"문의: {state['inquiry']}"
    )
    return {"category": msg.content.strip()}


def route_by_category(state: State) -> Literal["버그신고", "기능요청", "결제문의", "기타"]:
    """라우팅 함수 — 스테이트를 보고 다음 노드를 정한다. 노드가 아니라 함수다."""
    category = state["category"]
    if category in KNOWN_CATEGORIES:
        return category
    return "기타"  # Fallback — 예상 밖 분류는 전부 사람 검토로


def handle_bug(state: State) -> dict:
    return {"answer": "[버그 처리대] 재현 절차를 요청하고 이슈를 등록했습니다."}


def handle_feature(state: State) -> dict:
    return {"answer": "[기능 검토대] 제품 백로그에 추가하고 우선순위를 검토합니다."}


def handle_payment(state: State) -> dict:
    return {"answer": "[결제 상담대] 결제 이력을 조회해 환불 절차를 안내합니다."}


def handle_other(state: State) -> dict:
    return {"answer": "[사람 검토대] 자동 분류가 어려워 상담원에게 전달합니다."}


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("handle_bug", handle_bug)
builder.add_node("handle_feature", handle_feature)
builder.add_node("handle_payment", handle_payment)
builder.add_node("handle_other", handle_other)

builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    route_by_category,
    {
        "버그신고": "handle_bug",
        "기능요청": "handle_feature",
        "결제문의": "handle_payment",
        "기타": "handle_other",
    },
)
for name in ["handle_bug", "handle_feature", "handle_payment", "handle_other"]:
    builder.add_edge(name, END)

graph = builder.compile()


INQUIRIES = [
    "앱에서 사진을 올리면 화면이 하얗게 멈춰요",
    "다크 모드를 추가해 주시면 좋겠어요",
    "카드 결제가 두 번 청구된 것 같아요",
    "혹시 오늘 우주 날씨는 어떤가요?",
]


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    for inquiry in INQUIRIES:
        result = graph.invoke({"inquiry": inquiry})
        print(f"문의: {inquiry}")
        print(f"  분류: {result['category']}  →  {result['answer']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
