# -*- coding: utf-8 -*-
"""프로젝트 B: 시장 조사 보고서 파이프라인 (08-7).

세 관점(시장·경쟁·규제)을 병렬 조사(AI·최소 모델)
→ 코드 검증(관점별 최소 2건 + 근거 유형, 미달 시 재조사 루프)
→ 보고서 종합(AI·상위 모델) → 방향 결정 사람 승인(interrupt)

병렬 노드들이 서로 다른 필드에 쓰므로 리듀서가 필요 없습니다(06-2 참고).
재조사 때 자연스럽게 덮어쓰기가 되는 것도 이 설계 덕입니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python research_pipeline.py
"""
import json
import os
import sys
from typing import Literal, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402


def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
        temperature=0,
    )


small_llm = make_llm(os.environ.get("OPENAI_MODEL_SMALL", "gpt-5.6-luna"))
large_llm = make_llm(os.environ.get("OPENAI_MODEL_LARGE", "gpt-5.6-terra"))

MIN_FACTS = 2
MAX_ROUNDS = 2
ASPECT_FIELDS = {"시장": "market_facts", "경쟁": "competitor_facts", "규제": "policy_facts"}


class State(TypedDict):
    """조사 건 하나의 서류철 — 관점마다 자기 칸이 있다."""

    topic: str
    market_facts: list[dict]      # research_market 이 채운다 (덮어쓰기)
    competitor_facts: list[dict]  # research_competitor 가 채운다
    policy_facts: list[dict]      # research_policy 가 채운다
    issues: str                   # verify 가 채운다
    rounds: int                   # kickoff 가 올린다
    report: str                   # compose 가 채운다
    decision: str
    status: str


def kickoff(state: State) -> dict:
    """[코드] 조사 라운드 시작점 — 루프백의 목적지 역할."""
    return {"rounds": state.get("rounds", 0) + 1}


def _research(state: State, aspect: str) -> list[dict]:
    prompt = (
        f"'{state['topic']}'를 {aspect} 관점에서 조사하세요.\n"
        f"핵심 사실 {MIN_FACTS}건 이상, 각 사실은 한 문장, "
        "근거 유형은 연구/사례/통계 중 하나.\n"
        '다음 JSON 형식으로만 답하세요: {"facts": [{"text": "...", "evidence": "연구|사례|통계"}]}'
    )
    if state.get("issues"):
        prompt += f"\n직전 조사의 문제: {state['issues']}. 보완하세요."
    return json.loads(small_llm.invoke(prompt).content.strip())["facts"]


def research_market(state: State) -> dict:
    return {"market_facts": _research(state, "시장")}


def research_competitor(state: State) -> dict:
    return {"competitor_facts": _research(state, "경쟁")}


def research_policy(state: State) -> dict:
    return {"policy_facts": _research(state, "규제")}


def verify(state: State) -> dict:
    """[코드] 관점별로 최소 건수와 근거 유형을 검사한다."""
    problems = []
    for aspect, field in ASPECT_FIELDS.items():
        facts = state[field]
        if len(facts) < MIN_FACTS:
            problems.append(f"{aspect} 조사 부족: {len(facts)}건")
        for fact in facts:
            if fact.get("evidence") not in {"연구", "사례", "통계"}:
                problems.append(f"{aspect} 근거 유형 오류")
    return {"issues": " / ".join(problems)}


def route_verify(state: State) -> Literal["compose", "kickoff", "manual"]:
    if not state["issues"]:
        return "compose"
    if state["rounds"] >= MAX_ROUNDS:
        return "manual"
    return "kickoff"  # 세 관점 전체 재조사 (덮어쓰기 필드라 안전)


def compose(state: State) -> dict:
    """[AI·상위 모델] 보고서 종합 — 검증 통과한 사실들만 재료로 쓴다."""
    sections = []
    for aspect, field in ASPECT_FIELDS.items():
        listing = "\n".join(f"- {f['text']} ({f['evidence']})" for f in state[field])
        sections.append(f"[{aspect}]\n{listing}")
    msg = large_llm.invoke(
        f"다음은 '{state['topic']}'에 대해 검증을 마친 조사 결과입니다.\n\n"
        + "\n\n".join(sections)
        + "\n\n보고서 제목 한 줄과 세 문장 요약, 그리고 권고 한 문장을 작성하세요."
    )
    return {"report": msg.content.strip()}


def approval(state: State) -> dict:
    """[사람] 방향 결정 — 보고서를 확정할지 보완할지는 전략적 판단이다."""
    decision = interrupt(
        {
            "질문": "보고서를 확정할까요?",
            "조사 라운드": state["rounds"],
            "보고서": state["report"],
            "선택지": ["확정", "보완"],
        }
    )
    return {"decision": decision}


def route_decision(state: State) -> Literal["finalize", "manual"]:
    return "finalize" if state["decision"] == "확정" else "manual"


def finalize(state: State) -> dict:
    total = sum(len(state[f]) for f in ASPECT_FIELDS.values())
    return {"status": f"보고서 확정 — 사실 {total}건, 조사 {state['rounds']}라운드"}


def manual(state: State) -> dict:
    return {"status": f"담당자 검토로 전환 ({state.get('issues') or state.get('decision')})"}


builder = StateGraph(State)
for name, fn in [("kickoff", kickoff), ("research_market", research_market),
                 ("research_competitor", research_competitor),
                 ("research_policy", research_policy), ("verify", verify),
                 ("compose", compose), ("approval", approval),
                 ("finalize", finalize), ("manual", manual)]:
    builder.add_node(name, fn)

builder.add_edge(START, "kickoff")
for name in ["research_market", "research_competitor", "research_policy"]:
    builder.add_edge("kickoff", name)   # 팬아웃
    builder.add_edge(name, "verify")    # 팬인
builder.add_conditional_edges("verify", route_verify,
                              {"compose": "compose", "kickoff": "kickoff", "manual": "manual"})
builder.add_edge("compose", "approval")
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

    config = {"configurable": {"thread_id": "research-101"}, "callbacks": callbacks}
    result = graph.invoke({"topic": "국내 중소기업용 급여 아웃소싱 서비스"}, config)

    pending = result["__interrupt__"][0].value
    print(f"== 승인 대기 (조사 {pending['조사 라운드']}라운드) ==")
    print(pending["보고서"])
    print()

    result = graph.invoke(Command(resume="확정"), config)
    print(f"== 결과: {result['status']}")

    if langfuse is not None:
        langfuse.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
