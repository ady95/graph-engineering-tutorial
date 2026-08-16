# -*- coding: utf-8 -*-
"""조사에서 요약까지 — 두 노드 그래프 실습 (03-4).

graph_minimal.py 와 뼈대가 완전히 같습니다.
노드 함수 속만 진짜 LLM 호출로 바뀌었습니다.

준비:
    .env 에 OPENAI_API_KEY 설정
    (LANGFUSE_* 를 채우면 실행 추적도 함께 전송됩니다 — 없어도 동작)

실행:
    uv run python research_summary.py
"""
import os
import sys
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,  # 비우면 공식 API
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)


class State(TypedDict):
    """노드 사이를 오가는 데이터."""

    topic: str      # 입력: 조사 주제
    research: str   # research 노드가 채운다
    summary: str    # summarize 노드가 채운다


def research(state: State) -> dict:
    """조사 노드 — 주제의 핵심 사실을 모은다."""
    msg = llm.invoke(
        f"'{state['topic']}'에 대한 핵심 사실 3가지를 각각 한 문장으로 쓰세요. "
        "1. 2. 3. 번호를 붙이고, 확실한 사실만 쓰세요."
    )
    return {"research": msg.content}


def summarize(state: State) -> dict:
    """요약 노드 — 조사 결과를 두 문장 이내로 줄인다."""
    msg = llm.invoke(
        f"다음 조사 결과를 두 문장 이내로 요약하세요.\n\n{state['research']}"
    )
    return {"summary": msg.content}


builder = StateGraph(State)
builder.add_node("research", research)
builder.add_node("summarize", summarize)
builder.add_edge(START, "research")
builder.add_edge("research", "summarize")
builder.add_edge("summarize", END)
graph = builder.compile()


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        print(".env.example 을 .env 로 복사하고 값을 채우세요.")
        return 1

    # Langfuse 키가 있으면 추적을 붙인다 (02-7). 없으면 그냥 실행한다.
    callbacks = []
    langfuse = None
    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler

        langfuse = get_client()
        callbacks.append(CallbackHandler())
        print("Langfuse 추적: 켜짐")
    else:
        print("Langfuse 추적: 꺼짐 (LANGFUSE_PUBLIC_KEY 없음)")
    print()

    result = graph.invoke(
        {"topic": "전기차 배터리 재활용"},
        config={"callbacks": callbacks},
    )

    print("== research 노드가 채운 것 ==")
    print(result["research"])
    print()
    print("== summarize 노드가 채운 것 ==")
    print(result["summary"])

    if langfuse is not None:
        langfuse.flush()
        print()
        print("트레이스 전송 완료. 반영까지 10초 정도 걸립니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
