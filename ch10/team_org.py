# -*- coding: utf-8 -*-
"""실습: 조사팀·작성팀·검수팀 3팀 조직 (10-5).

세 팀은 각각 서브그래프이고, 최상위 슈퍼바이저가 팀 단위로 위임합니다.
- 팀마다 쓰는 모델·규칙이 다르다 (조직 그래프의 권한 분리)
- 검수팀이 반려하면 작성팀으로 되돌아간다 (반려 2회면 사람에게)

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python team_org.py
"""
import os
import sys
from typing import Literal, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402


def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
        temperature=0,
    )


small_llm = make_llm(os.environ.get("OPENAI_MODEL_SMALL", "gpt-5.6-luna"))
large_llm = make_llm(os.environ.get("OPENAI_MODEL_LARGE", "gpt-5.6-terra"))

MAX_REJECTS = 2


# ── 공유 스테이트: 팀 사이를 오가는 것만 담는다 ────────────────
class OrgState(TypedDict):
    task: str
    findings: str    # 조사팀의 산출물
    draft: str       # 작성팀의 산출물
    verdict: str     # 검수팀의 판정 사유
    passed: bool
    rejects: int
    status: str


# ── 조사팀 (서브그래프): 최소 모델, 수집→정리 2단계 ─────────────
class ResearchTeamState(TypedDict):
    task: str
    raw: str
    findings: str


def r_collect(state: ResearchTeamState) -> dict:
    msg = small_llm.invoke(f"'{state['task']}'에 필요한 사실 3가지를 한 문장씩 쓰세요.")
    return {"raw": msg.content.strip()}


def r_organize(state: ResearchTeamState) -> dict:
    return {"findings": state["raw"]}  # 실무라면 정제·중복 제거가 들어갈 자리


_rb = StateGraph(ResearchTeamState)
_rb.add_node("collect", r_collect)
_rb.add_node("organize", r_organize)
_rb.add_edge(START, "collect")
_rb.add_edge("collect", "organize")
_rb.add_edge("organize", END)
research_team = _rb.compile()


# ── 작성팀 (서브그래프): 상위 모델, 반려 사유를 반영해 다시 쓴다 ──
class WriteTeamState(TypedDict):
    task: str
    findings: str
    verdict: str
    draft: str


def w_write(state: WriteTeamState) -> dict:
    prompt = (
        f"다음 사실로 '{state['task']}' 공지 초안을 쓰세요. 3문장 이내, "
        f"끝인사는 '감사합니다.'로.\n{state['findings']}"
    )
    if state.get("verdict"):
        prompt += f"\n직전 반려 사유: {state['verdict']}. 해결해 다시 쓰세요."
    msg = large_llm.invoke(prompt)
    return {"draft": msg.content.strip()}


_wb = StateGraph(WriteTeamState)
_wb.add_node("write", w_write)
_wb.add_edge(START, "write")
_wb.add_edge("write", END)
write_team = _wb.compile()


# ── 검수팀 (코드): 쓰기 권한이 없다 — 판정만 한다 ────────────────
def review_team(state: OrgState) -> dict:
    problems = []
    draft = state["draft"]
    if "감사합니다." not in draft:
        problems.append("끝인사 규칙 위반")
    if draft.count(".") > 4:
        problems.append("3문장 초과 의심")
    if problems:
        return {"passed": False, "verdict": " / ".join(problems),
                "rejects": state.get("rejects", 0) + 1}
    return {"passed": True, "verdict": "규칙 통과"}


# ── 최상위 조직: 팀 단위의 흐름 ────────────────────────────────
def call_research(state: OrgState) -> dict:
    result = research_team.invoke({"task": state["task"]})
    return {"findings": result["findings"]}


def call_write(state: OrgState) -> dict:
    result = write_team.invoke(
        {"task": state["task"], "findings": state["findings"], "verdict": state.get("verdict", "")}
    )
    return {"draft": result["draft"]}


def route_review(state: OrgState) -> Literal["done", "call_write", "escalate"]:
    if state["passed"]:
        return "done"
    if state["rejects"] >= MAX_REJECTS:
        return "escalate"
    return "call_write"  # 반려 사유를 들고 작성팀으로


def done(state: OrgState) -> dict:
    return {"status": f"게시 확정 (반려 {state.get('rejects', 0)}회)"}


def escalate(state: OrgState) -> dict:
    return {"status": f"반려 {MAX_REJECTS}회 — 사람 검토로 이관"}


builder = StateGraph(OrgState)
builder.add_node("call_research", call_research)
builder.add_node("call_write", call_write)
builder.add_node("review_team", review_team)
builder.add_node("done", done)
builder.add_node("escalate", escalate)

builder.add_edge(START, "call_research")
builder.add_edge("call_research", "call_write")
builder.add_edge("call_write", "review_team")
builder.add_conditional_edges("review_team", route_review,
                              {"done": "done", "call_write": "call_write", "escalate": "escalate"})
builder.add_edge("done", END)
builder.add_edge("escalate", END)

graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    result = graph.invoke({"task": "10월 전사 워크숍 일정 안내", "rejects": 0})
    print(f"결과: {result['status']}")
    print(f"검수 판정: {result['verdict']}")
    print()
    print("== 최종 초안 ==")
    print(result["draft"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
