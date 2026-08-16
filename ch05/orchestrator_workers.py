# -*- coding: utf-8 -*-
"""패턴 3: 오케스트레이터-워커 — 동적 작업 분할 (05-4).

플래너(오케스트레이터)가 실행 시점에 하위 주제를 정하고,
Send로 주제 수만큼 워커를 만들어 병렬 위임합니다.
워커 개수는 입력마다 달라집니다 — 그래서 '동적' 팬아웃입니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python orchestrator_workers.py
"""
import json
import operator
import os
import sys
from typing import Annotated, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Send  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

MAX_WORKERS = 5  # 워커 수 상한 — 플래너가 폭주해도 여기서 막힌다


class State(TypedDict):
    """메인 그래프의 스테이트."""

    topic: str
    subtopics: list[str]                       # plan 노드가 채운다
    notes: Annotated[list[str], operator.add]  # 워커들이 동시에 추가한다
    digest: str                                # gather 노드가 채운다


class WorkerInput(TypedDict):
    """워커가 받는 입력 — 메인 스테이트가 아니라 Send가 실어 보낸 것."""

    subtopic: str


def plan(state: State) -> dict:
    """오케스트레이터 — 실행 시점에 하위 주제를 정한다. 개수는 주제에 달렸다."""
    msg = llm.invoke(
        f"'{state['topic']}'를 조사하려 합니다. 꼭 필요한 하위 주제를 2~5개 정하세요.\n"
        '다음 JSON 형식으로만 답하세요: {"subtopics": ["하위 주제", ...]}'
    )
    subtopics = json.loads(msg.content.strip())["subtopics"][:MAX_WORKERS]
    return {"subtopics": subtopics}


def fan_out(state: State) -> list[Send]:
    """하위 주제 수만큼 worker 노드 실행을 만들어 낸다."""
    return [Send("worker", {"subtopic": s}) for s in state["subtopics"]]


def worker(state: WorkerInput) -> dict:
    """워커 — 자기 하위 주제 하나만 조사한다."""
    msg = llm.invoke(f"'{state['subtopic']}'의 핵심을 두 문장으로 정리하세요.")
    return {"notes": [f"[{state['subtopic']}] {msg.content}"]}


def gather(state: State) -> dict:
    """팬인 — 모든 워커가 끝난 뒤 결과를 취합한다."""
    return {"digest": f"하위 주제 {len(state['subtopics'])}개, 노트 {len(state['notes'])}건 취합"}


builder = StateGraph(State)
builder.add_node("plan", plan)
builder.add_node("worker", worker)
builder.add_node("gather", gather)

builder.add_edge(START, "plan")
builder.add_conditional_edges("plan", fan_out, ["worker"])  # 동적 팬아웃
builder.add_edge("worker", "gather")
builder.add_edge("gather", END)

graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    for topic in ["사내 문서 검색 챗봇 도입", "점심 메뉴 추천 기능"]:
        result = graph.invoke({"topic": topic})
        print(f"주제: {topic}")
        print(f"  플래너가 정한 하위 주제 {len(result['subtopics'])}개: {result['subtopics']}")
        print(f"  {result['digest']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
