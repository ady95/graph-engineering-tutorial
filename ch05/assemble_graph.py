# -*- coding: utf-8 -*-
"""다섯 패턴을 하나의 그래프에 조립 (05-8).

classify(라우터) → plan(오케스트레이터) → worker들(동적 병렬)
→ verify(평가자·코드) → [미달이면 plan으로 루프백, 2회 상한]
→ approval(사람 승인) → finalize

준비:
    .env 에 OPENAI_API_KEY 설정
    (LANGFUSE_* 를 채우면 실행 추적도 함께 전송됩니다)

실행:
    uv run python assemble_graph.py
"""
import json
import operator
import os
import sys
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, Send, interrupt  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

KNOWN_KINDS = {"시장조사", "기술조사"}
MIN_NOTES = 3
MAX_ROUNDS = 2


class State(TypedDict):
    request: str                               # 입력: 조사 요청 원문
    kind: str                                  # classify가 채운다
    subtopics: list[str]                       # plan이 채운다
    notes: Annotated[list[str], operator.add]  # worker들이 추가한다
    passed: bool                               # verify가 채운다
    check_report: str                          # verify가 채운다
    rounds: int                                # plan이 올린다 — 루프 상한 근거
    decision: str                              # approval이 채운다
    result: str                                # finalize가 채운다


class WorkerInput(TypedDict):
    subtopic: str


def classify(state: State) -> dict:
    """패턴 1 라우터의 분류 노드."""
    msg = llm.invoke(
        "다음 요청을 시장조사/기술조사 중 하나로 분류하세요. 해당 단어만 답하세요.\n"
        f"요청: {state['request']}"
    )
    return {"kind": msg.content.strip()}


def route_kind(state: State) -> Literal["plan", "manual"]:
    """Fallback 포함 — 분류가 예상 밖이면 사람에게."""
    if state["kind"] in KNOWN_KINDS:
        return "plan"
    return "manual"


def plan(state: State) -> dict:
    """패턴 3 오케스트레이터 — 하위 주제를 실행 시점에 정한다."""
    prompt = (
        f"'{state['request']}'에 대한 {state['kind']}를 계획하세요. "
        "하위 주제 3~4개를 정하세요.\n"
        '다음 JSON 형식으로만 답하세요: {"subtopics": ["하위 주제", ...]}'
    )
    if state.get("check_report") and not state.get("passed", True):
        prompt += f"\n직전 계획의 문제: {state['check_report']}. 보완해 다시 계획하세요."
    subtopics = json.loads(llm.invoke(prompt).content.strip())["subtopics"][:5]
    return {"subtopics": subtopics, "rounds": state.get("rounds", 0) + 1}


def fan_out(state: State) -> list[Send]:
    """패턴 2·3 — 하위 주제 수만큼 워커를 동적 생성."""
    return [Send("worker", {"subtopic": s}) for s in state["subtopics"]]


def worker(state: WorkerInput) -> dict:
    msg = llm.invoke(
        f"'{state['subtopic']}'를 조사해 핵심 사실 한 문장을 쓰고, "
        "끝에 근거 유형을 (연구)/(사례)/(통계) 중 하나로 표시하세요."
    )
    return {"notes": [f"[{state['subtopic']}] {msg.content.strip()}"]}


def verify(state: State) -> dict:
    """패턴 4 평가자 — 코드로 검사한다."""
    problems = []
    fresh = state["notes"]
    if len(fresh) < MIN_NOTES:
        problems.append(f"노트 부족: {len(fresh)}건 (최소 {MIN_NOTES}건)")
    for i, note in enumerate(fresh, 1):
        if not any(tag in note for tag in ["(연구)", "(사례)", "(통계)"]):
            problems.append(f"{i}번 근거 유형 없음")
    if problems:
        return {"passed": False, "check_report": " / ".join(problems)}
    return {"passed": True, "check_report": f"노트 {len(fresh)}건 검증 통과"}


def route_verify(state: State) -> Literal["approval", "plan", "manual"]:
    """패턴 4의 루프백 + 상한."""
    if state["passed"]:
        return "approval"
    if state["rounds"] >= MAX_ROUNDS:
        return "manual"
    return "plan"


def approval(state: State) -> dict:
    """패턴 5 — 최종 보고 전 사람 승인."""
    decision = interrupt(
        {
            "질문": "조사 결과를 확정할까요?",
            "검증": state["check_report"],
            "노트": state["notes"],
        }
    )
    return {"decision": decision}


def route_decision(state: State) -> Literal["finalize", "manual"]:
    if state["decision"] == "승인":
        return "finalize"
    return "manual"


def finalize(state: State) -> dict:
    return {"result": f"확정 — {state['kind']} 노트 {len(state['notes'])}건 (계획 {state['rounds']}회)"}


def manual(state: State) -> dict:
    return {"result": "자동 처리 범위를 벗어나 사람 담당자에게 전달"}


builder = StateGraph(State)
for name, fn in [("classify", classify), ("plan", plan), ("worker", worker),
                 ("verify", verify), ("approval", approval),
                 ("finalize", finalize), ("manual", manual)]:
    builder.add_node(name, fn)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route_kind, {"plan": "plan", "manual": "manual"})
builder.add_conditional_edges("plan", fan_out, ["worker"])
builder.add_edge("worker", "verify")
builder.add_conditional_edges("verify", route_verify,
                              {"approval": "approval", "plan": "plan", "manual": "manual"})
builder.add_conditional_edges("approval", route_decision,
                              {"finalize": "finalize", "manual": "manual"})
builder.add_edge("finalize", END)
builder.add_edge("manual", END)

graph = builder.compile(checkpointer=InMemorySaver())


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    callbacks = []
    langfuse = None
    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler

        langfuse = get_client()
        callbacks.append(CallbackHandler())

    config = {"configurable": {"thread_id": "research-001"}, "callbacks": callbacks}

    result = graph.invoke({"request": "중견 물류기업의 창고 자동화 로봇 도입"}, config)
    pending = result["__interrupt__"][0].value
    print("== 승인 대기 상태 ==")
    print(f"질문: {pending['질문']} / 검증: {pending['검증']}")
    for note in pending["노트"]:
        print("-", note[:70])
    print()

    result = graph.invoke(Command(resume="승인"), config)
    print("== 재개 후 최종 결과 ==")
    print(result["result"])

    if langfuse is not None:
        langfuse.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
