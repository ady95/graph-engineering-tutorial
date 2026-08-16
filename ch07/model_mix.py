# -*- coding: utf-8 -*-
"""노드마다 다른 모델 쓰기 — 배분 전후 비교 (07-3).

같은 파이프라인(분류 → 답변 작성)을 두 구성으로 실행합니다.
A안: 두 노드 모두 상위 모델
B안: 분류는 최소 모델, 답변 작성만 상위 모델

준비:
    .env 에 OPENAI_API_KEY 설정
    (LANGFUSE_* 를 채우면 비용이 트레이스에 집계됩니다)

실행:
    uv run python model_mix.py
"""
import os
import sys
import time
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

SMALL_MODEL = os.environ.get("OPENAI_MODEL_SMALL", "gpt-5.6-luna")
LARGE_MODEL = os.environ.get("OPENAI_MODEL_LARGE", "gpt-5.6-terra")


def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
        temperature=0,
    )


class State(TypedDict):
    inquiry: str
    category: str
    reply: str


def build(classify_model: str, reply_model: str):
    classify_llm = make_llm(classify_model)
    reply_llm = make_llm(reply_model)

    def classify(state: State) -> dict:
        msg = classify_llm.invoke(
            "다음 문의를 버그신고/기능요청/결제문의 중 하나로 분류하세요. 해당 단어만 답하세요.\n"
            f"문의: {state['inquiry']}"
        )
        return {"category": msg.content.strip()}

    def reply(state: State) -> dict:
        msg = reply_llm.invoke(
            f"고객 문의({state['category']})에 대한 정중한 답변을 3문장으로 작성하세요.\n"
            f"문의: {state['inquiry']}"
        )
        return {"reply": msg.content}

    builder = StateGraph(State)
    builder.add_node("classify", classify)
    builder.add_node("reply", reply)
    builder.add_edge(START, "classify")
    builder.add_edge("classify", "reply")
    builder.add_edge("reply", END)
    return builder.compile()


INQUIRY = "카드 결제가 두 번 청구된 것 같아요. 확인 부탁드립니다."


def run(label: str, classify_model: str, reply_model: str, callbacks: list) -> None:
    graph = build(classify_model, reply_model)
    t0 = time.perf_counter()
    result = graph.invoke(
        {"inquiry": INQUIRY},
        config={"callbacks": callbacks, "metadata": {"langfuse_tags": [label]}},
    )
    elapsed = time.perf_counter() - t0
    print(f"[{label}] classify={classify_model} / reply={reply_model}")
    print(f"  소요 {elapsed:.2f}초 / 분류: {result['category']}")
    print(f"  답변 머리: {result['reply'][:60]}")
    print()


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

    run("A안-전부-상위모델", LARGE_MODEL, LARGE_MODEL, callbacks)
    run("B안-분류만-최소모델", SMALL_MODEL, LARGE_MODEL, callbacks)

    if langfuse is not None:
        langfuse.flush()
        print("두 실행의 노드별 비용은 Langfuse에서 확인하세요 (measure_costs.py 참고).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
