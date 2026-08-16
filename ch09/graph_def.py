# -*- coding: utf-8 -*-
"""서버에 얹을 그래프 정의 (09-2, 09-3 공용).

03장의 조사 → 요약 그래프를 비동기 노드로 옮긴 것입니다.
서버에서는 동시 요청을 막지 않도록 노드도 비동기로 씁니다.
"""
import os
from typing import TypedDict

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


class State(TypedDict):
    topic: str
    research: str
    summary: str


async def research(state: State) -> dict:
    msg = await llm.ainvoke(
        f"'{state['topic']}'에 대한 핵심 사실 3가지를 각각 한 문장으로 쓰세요."
    )
    return {"research": msg.content}


async def summarize(state: State) -> dict:
    msg = await llm.ainvoke(
        f"다음 조사 결과를 한 문장으로 요약하세요.\n\n{state['research']}"
    )
    return {"summary": msg.content}


builder = StateGraph(State)
builder.add_node("research", research)
builder.add_node("summarize", summarize)
builder.add_edge(START, "research")
builder.add_edge("research", "summarize")
builder.add_edge("summarize", END)

graph = builder.compile()  # 서버 기동 시(모듈 임포트 시) 한 번만 컴파일된다
