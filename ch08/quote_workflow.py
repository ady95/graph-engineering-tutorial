# -*- coding: utf-8 -*-
"""프로젝트 A: 견적·승인 워크플로우 (08-6).

접수(코드) → 분류(AI·최소 모델) → 단가 계산(코드)
→ 견적서 작성(AI·상위 모델) → 품질 검토(코드, 루프백)
→ 발송 전 사람 승인(interrupt) → 발송

준비:
    .env 에 OPENAI_API_KEY 설정
    (LANGFUSE_* 를 채우면 실행 추적도 함께 전송됩니다)

실행:
    uv run python quote_workflow.py
"""
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

REQUIRED_FIELDS = ["고객명", "요청내용", "규모", "납기"]
PRICE_TABLE = {"챗봇구축": 8_000_000, "데이터분석": 5_000_000, "유지보수": 1_500_000}
SCALE_MULTIPLIER = {"소": 1.0, "중": 1.8, "대": 3.0}
MAX_REVISIONS = 2


class State(TypedDict):
    """견적 건 하나가 흘러가는 서류철."""

    request: dict     # 입력: 견적 요청 원본
    issues: str       # intake·review 가 채운다 (문제 사유)
    service_type: str
    price: int
    quote_doc: str
    attempts: int
    decision: str
    status: str


def intake(state: State) -> dict:
    """[코드] 접수 — 필수 항목이 다 있는지 검사한다."""
    missing = [f for f in REQUIRED_FIELDS if not state["request"].get(f)]
    if missing:
        return {"issues": f"필수 항목 누락: {', '.join(missing)}"}
    return {"issues": ""}


def route_intake(state: State) -> Literal["classify", "manual"]:
    return "manual" if state["issues"] else "classify"


def classify(state: State) -> dict:
    """[AI·최소 모델] 분류 — 요청 내용으로 서비스 유형을 판단한다."""
    msg = small_llm.invoke(
        "다음 요청을 챗봇구축/데이터분석/유지보수 중 하나로 분류하세요. "
        "확신이 없으면 '기타'라고 답하세요. 해당 단어만 답하세요.\n"
        f"요청: {state['request']['요청내용']}"
    )
    return {"service_type": msg.content.strip()}


def route_classify(state: State) -> Literal["calculate", "manual"]:
    return "calculate" if state["service_type"] in PRICE_TABLE else "manual"


def calculate(state: State) -> dict:
    """[코드] 단가 계산 — 단가표 × 규모 배율. AI에게 시킬 이유가 없다."""
    base = PRICE_TABLE[state["service_type"]]
    multiplier = SCALE_MULTIPLIER.get(state["request"]["규모"], 1.0)
    return {"price": int(base * multiplier)}


def compose(state: State) -> dict:
    """[AI·상위 모델] 견적서 작성 — 고객에게 나가는 문안이므로 품질 우선."""
    prompt = (
        "다음 정보로 견적서 본문을 작성하세요.\n"
        f"- 고객명: {state['request']['고객명']}\n"
        f"- 서비스: {state['service_type']}\n"
        f"- 금액: {state['price']:,}원 (부가세 별도)\n"
        f"- 납기: {state['request']['납기']}\n"
        "규칙: 금액과 납기를 본문에 명시할 것. '유효기간 30일' 문구를 포함할 것. "
        "정중한 어조로 4문장 이내."
    )
    if state.get("issues") and state.get("attempts", 0) > 0:
        prompt += f"\n직전 초안의 문제: {state['issues']}. 해결해 다시 작성하세요."
    msg = large_llm.invoke(prompt)
    return {"quote_doc": msg.content.strip(), "attempts": state.get("attempts", 0) + 1}


def review(state: State) -> dict:
    """[코드] 품질 검토 — 필수 요소가 문안에 실제로 들어갔는지 검사한다."""
    problems = []
    doc = state["quote_doc"]
    if f"{state['price']:,}" not in doc:
        problems.append("금액 표기 누락")
    if "유효기간" not in doc:
        problems.append("유효기간 문구 누락")
    if state["request"]["납기"] not in doc:
        problems.append("납기 누락")
    return {"issues": " / ".join(problems)}


def route_review(state: State) -> Literal["approval", "compose", "manual"]:
    if not state["issues"]:
        return "approval"
    if state["attempts"] >= MAX_REVISIONS:
        return "manual"
    return "compose"


def approval(state: State) -> dict:
    """[사람] 발송 전 승인 — 고객에게 나가는 되돌릴 수 없는 행동의 직전."""
    decision = interrupt(
        {
            "질문": "이 견적서를 고객에게 발송할까요?",
            "고객": state["request"]["고객명"],
            "금액": f"{state['price']:,}원",
            "견적서": state["quote_doc"],
            "선택지": ["승인", "반려"],
        }
    )
    return {"decision": decision}


def route_decision(state: State) -> Literal["send", "manual"]:
    return "send" if state["decision"] == "승인" else "manual"


def send(state: State) -> dict:
    return {"status": f"발송 완료 — {state['request']['고객명']} / {state['price']:,}원"}


def manual(state: State) -> dict:
    reason = state["issues"] or state.get("decision") or state.get("service_type", "")
    return {"status": f"담당자 검토로 전환 ({reason})"}


builder = StateGraph(State)
for name, fn in [("intake", intake), ("classify", classify), ("calculate", calculate),
                 ("compose", compose), ("review", review), ("approval", approval),
                 ("send", send), ("manual", manual)]:
    builder.add_node(name, fn)

builder.add_edge(START, "intake")
builder.add_conditional_edges("intake", route_intake, {"classify": "classify", "manual": "manual"})
builder.add_conditional_edges("classify", route_classify, {"calculate": "calculate", "manual": "manual"})
builder.add_edge("calculate", "compose")
builder.add_edge("compose", "review")
builder.add_conditional_edges("review", route_review,
                              {"approval": "approval", "compose": "compose", "manual": "manual"})
builder.add_conditional_edges("approval", route_decision, {"send": "send", "manual": "manual"})
builder.add_edge("send", END)
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

    # ── 건 1: 정상 요청 — 승인까지 완주 ─────────────────────────
    request = {
        "고객명": "한빛물류",
        "요청내용": "창고 재고 문의에 자동 응답하는 사내 챗봇을 만들고 싶습니다",
        "규모": "중",
        "납기": "10월 말",
    }
    config = {"configurable": {"thread_id": "quote-101"}, "callbacks": callbacks}
    result = graph.invoke({"request": request, "attempts": 0}, config)

    pending = result["__interrupt__"][0].value
    print("== 승인 대기 ==")
    print(f"고객: {pending['고객']} / 금액: {pending['금액']}")
    print(f"견적서:\n{pending['견적서']}")
    print()

    result = graph.invoke(Command(resume="승인"), config)
    print(f"== 건 1 결과: {result['status']} (작성 {result['attempts']}회)")
    print()

    # ── 건 2: 필수 항목이 빠진 요청 — Fallback 확인 ─────────────
    bad_request = {"고객명": "미림상사", "요청내용": "견적 좀 주세요", "규모": "", "납기": ""}
    config2 = {"configurable": {"thread_id": "quote-102"}, "callbacks": callbacks}
    result = graph.invoke({"request": bad_request, "attempts": 0}, config2)
    print(f"== 건 2 결과: {result['status']}")

    if langfuse is not None:
        langfuse.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
