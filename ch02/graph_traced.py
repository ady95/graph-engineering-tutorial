# -*- coding: utf-8 -*-
"""Langfuse 연결 확인용 그래프 (02-7).

`graph.py`에 노드 하나를 더하고 Langfuse 추적을 붙인 것입니다.
LLM을 호출하지 않으므로 OpenAI API 키 없이도 동작합니다.

준비:
    .env 에 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL 설정

실행:
    uv run python graph_traced.py
"""
import os
import sys
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

load_dotenv()

from langfuse import get_client  # noqa: E402
from langfuse.langchain import CallbackHandler  # noqa: E402


class State(TypedDict):
    topic: str
    collected: str
    checked: str
    summary: str


def collect(state: State) -> dict:
    """조사 노드."""
    return {"collected": f"'{state['topic']}' 자료 3건 수집"}


def verify(state: State) -> dict:
    """검증 노드 — 코드로 규칙을 확인합니다. AI를 쓰지 않습니다."""
    ok = "3건" in state["collected"]
    return {"checked": f"검증 결과: {'통과' if ok else '미달'}"}


def summarize(state: State) -> dict:
    """요약 노드."""
    return {"summary": f"[요약] {state['collected']} / {state['checked']}"}


builder = StateGraph(State)
builder.add_node("collect", collect)
builder.add_node("verify", verify)
builder.add_node("summarize", summarize)
builder.add_edge(START, "collect")
builder.add_edge("collect", "verify")
builder.add_edge("verify", "summarize")
builder.add_edge("summarize", END)

graph = builder.compile()


def main() -> int:
    required = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print("환경변수가 설정되지 않았습니다:", ", ".join(missing))
        print(".env.example 을 .env 로 복사하고 값을 채우세요.")
        return 1

    print(f"리전: {os.environ['LANGFUSE_BASE_URL']}")

    langfuse = get_client()
    if not langfuse.auth_check():
        print("인증 실패 — 키와 리전을 확인하세요.")
        print("리전마다 계정이 분리되어 있습니다. 키를 발급받은 리전과 BASE_URL이 같아야 합니다.")
        return 1
    print("인증 확인 완료")

    # 이 한 줄이 추적의 전부입니다. LangGraph 전용 설정은 없습니다.
    handler = CallbackHandler()

    result = graph.invoke(
        {"topic": "그래프 엔지니어링"},
        config={"callbacks": [handler]},
    )

    print()
    for key, value in result.items():
        print(f"{key}: {value}")

    # 프로그램이 짧게 끝나면 전송 전에 종료될 수 있습니다.
    langfuse.flush()
    print("\n트레이스 전송 완료. Langfuse 화면에서 확인하세요.")
    print("반영까지 10초 정도 걸립니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
