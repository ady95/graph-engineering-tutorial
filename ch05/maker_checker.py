# -*- coding: utf-8 -*-
"""패턴 4: 생성자-평가자 루프 (05-5, 05-6).

생성자(AI)가 공지문을 쓰고, 평가자(코드)가 규칙을 검사합니다.
반려되면 사유와 함께 생성자로 되돌아갑니다. 재시도는 3회로 제한합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python maker_checker.py
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

REQUIRED_WORDS = ["일시", "장소", "문의"]
MAX_LEN = 150
MAX_ATTEMPTS = 3


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    request: str    # 입력: 공지 요청 내용
    draft: str      # maker 노드가 채운다
    feedback: str   # checker 노드가 채운다 (반려 사유)
    approved: bool  # checker 노드가 채운다
    attempts: int   # maker 노드가 올린다 — 루프 제어의 근거

def maker(state: State) -> dict:
    """생성자 — 공지문을 쓴다. 반려 사유가 있으면 반영해 다시 쓴다."""
    prompt = f"다음 내용으로 사내 공지문을 작성하세요.\n{state['request']}"
    if state.get("feedback"):
        prompt += (
            f"\n\n직전 초안:\n{state['draft']}\n"
            f"검수 반려 사유: {state['feedback']}\n"
            "반려 사유를 전부 해결해 다시 작성하세요."
        )
    msg = llm.invoke(prompt)
    return {"draft": msg.content.strip(), "attempts": state.get("attempts", 0) + 1}


def checker(state: State) -> dict:
    """평가자 — 감이 아니라 서면화된 규칙으로 검사한다. LLM을 쓰지 않는다."""
    problems = []
    draft = state["draft"]
    for word in REQUIRED_WORDS:
        if word not in draft:
            problems.append(f"'{word}' 항목 누락")
    if len(draft) > MAX_LEN:
        problems.append(f"길이 초과: {len(draft)}자 (제한 {MAX_LEN}자)")

    if problems:
        return {"approved": False, "feedback": " / ".join(problems)}
    return {"approved": True, "feedback": ""}


def route_after_check(state: State) -> Literal["publish", "escalate", "maker"]:
    """루프 제어 — 통과·재시도·상한 초과를 여기서 가른다."""
    if state["approved"]:
        return "publish"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "escalate"  # 상한 도달 — 무한 루프 대신 사람에게
    return "maker"         # 반려 사유를 들고 생성자로 되돌아간다


def publish(state: State) -> dict:
    return {"feedback": f"게시 완료 (시도 {state['attempts']}회)"}


def escalate(state: State) -> dict:
    return {"feedback": f"{MAX_ATTEMPTS}회 반려 — 사람 검토로 넘깁니다"}


builder = StateGraph(State)
builder.add_node("maker", maker)
builder.add_node("checker", checker)
builder.add_node("publish", publish)
builder.add_node("escalate", escalate)

builder.add_edge(START, "maker")
builder.add_edge("maker", "checker")
builder.add_conditional_edges(
    "checker",
    route_after_check,
    {"publish": "publish", "escalate": "escalate", "maker": "maker"},
)
builder.add_edge("publish", END)
builder.add_edge("escalate", END)

graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    request = (
        "9월 5일 금요일 15시, 3층 대회의실에서 전사 보안 교육을 합니다. "
        "전 직원 필수 참석이고, 문의는 정보보안팀입니다."
    )

    result = graph.invoke({"request": request})
    print(f"시도 횟수: {result['attempts']}")
    print(f"최종 상태: {result['feedback']}")
    print(f"초안 길이: {len(result['draft'])}자")
    print()
    print("== 최종 초안 ==")
    print(result["draft"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
