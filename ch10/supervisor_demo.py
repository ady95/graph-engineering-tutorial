# -*- coding: utf-8 -*-
"""슈퍼바이저 패턴 — 관리자가 팀을 지휘한다 (10-2).

슈퍼바이저(AI)가 상황을 보고 조사원/작성자에게 반복 위임하고,
끝났다고 판단하면 종료합니다. 위임 횟수에는 상한이 있습니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python supervisor_demo.py
"""
import json
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

MAX_DELEGATIONS = 4
MEMBERS = {"researcher", "writer"}


class State(TypedDict):
    task: str
    notes: str        # researcher가 채운다
    draft: str        # writer가 채운다
    next_member: str  # supervisor가 정한다
    delegations: int  # supervisor가 올린다 — 위임 상한의 근거
    log: str


def supervisor(state: State) -> dict:
    """관리자 — 현재 상황을 보고 다음 위임(또는 종료)을 정한다."""
    status = (
        f"과제: {state['task']}\n"
        f"조사 노트: {'있음' if state.get('notes') else '없음'}\n"
        f"초안: {'있음' if state.get('draft') else '없음'}"
    )
    msg = llm.invoke(
        "당신은 팀 관리자입니다. 아래 상황을 보고 다음 행동을 정하세요.\n"
        f"{status}\n"
        "선택지: researcher(조사 필요할 때) / writer(조사가 있고 초안이 필요할 때) / done(초안까지 끝났을 때)\n"
        '다음 JSON 형식으로만 답하세요: {"next": "researcher|writer|done", "reason": "한 문장"}'
    )
    decision = json.loads(msg.content.strip())
    chosen = decision["next"] if decision["next"] in MEMBERS | {"done"} else "done"  # 코드 가드
    return {
        "next_member": chosen,
        "delegations": state.get("delegations", 0) + 1,
        "log": state.get("log", "") + f"\n  위임 {state.get('delegations', 0) + 1}: {chosen} — {decision.get('reason', '')}",
    }


def route_supervisor(state: State) -> Literal["researcher", "writer", "finish", "escalate"]:
    if state["next_member"] == "done":
        return "finish"
    if state["delegations"] > MAX_DELEGATIONS:
        return "escalate"  # 관리자가 결단을 못 내리면 사람에게
    return state["next_member"]


def researcher(state: State) -> dict:
    """팀원 1 — 조사만 한다. 결과만 보고하고 과정은 자기 안에 격리."""
    msg = llm.invoke(f"'{state['task']}'에 필요한 핵심 사실 2가지를 한 문장씩 쓰세요.")
    return {"notes": msg.content.strip()}


def writer(state: State) -> dict:
    """팀원 2 — 조사 노트로 초안만 쓴다."""
    msg = llm.invoke(f"다음 노트로 두 문장짜리 안내문 초안을 쓰세요.\n{state['notes']}")
    return {"draft": msg.content.strip()}


def finish(state: State) -> dict:
    return {"log": state["log"] + "\n  종료: 관리자가 완료 판단"}


def escalate(state: State) -> dict:
    return {"log": state["log"] + "\n  종료: 위임 상한 초과 — 사람 검토로"}


builder = StateGraph(State)
for name, fn in [("supervisor", supervisor), ("researcher", researcher),
                 ("writer", writer), ("finish", finish), ("escalate", escalate)]:
    builder.add_node(name, fn)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", route_supervisor,
                              {"researcher": "researcher", "writer": "writer",
                               "finish": "finish", "escalate": "escalate"})
builder.add_edge("researcher", "supervisor")  # 팀원은 일이 끝나면 관리자에게 돌아온다
builder.add_edge("writer", "supervisor")
builder.add_edge("finish", END)
builder.add_edge("escalate", END)

graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    result = graph.invoke({"task": "사내 보안 교육 참석 안내"})
    print("== 위임 기록 ==")
    print(result["log"].strip())
    print()
    print("== 최종 초안 ==")
    print(result["draft"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
