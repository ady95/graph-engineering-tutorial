# -*- coding: utf-8 -*-
"""스테이트의 부분 업데이트 확인 (03-2).

노드는 스테이트 전체를 돌려주는 것이 아니라
자기가 갱신할 부분만 돌려준다는 것을 눈으로 확인합니다.
LLM을 호출하지 않으므로 API 키 없이 동작합니다.

실행:
    uv run python state_demo.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    """노드 사이를 오가는 데이터의 스키마."""

    topic: str   # 입력으로 받는다. 어느 노드도 건드리지 않는다
    memo: str    # write_memo 노드가 채운다
    stamp: str   # approve 노드가 채운다


def write_memo(state: State) -> dict:
    """memo 필드 하나만 돌려준다. topic은 그대로 유지되는가?"""
    print(f"  [write_memo] 받은 스테이트: {state}")
    return {"memo": f"'{state['topic']}' 검토가 필요합니다"}


def approve(state: State) -> dict:
    """stamp 필드 하나만 돌려준다. topic과 memo는 그대로 유지되는가?"""
    print(f"  [approve]    받은 스테이트: {state}")
    return {"stamp": "확인 완료"}


builder = StateGraph(State)
builder.add_node("write_memo", write_memo)
builder.add_node("approve", approve)
builder.add_edge(START, "write_memo")
builder.add_edge("write_memo", "approve")
builder.add_edge("approve", END)
graph = builder.compile()


if __name__ == "__main__":
    print("초기 입력: {'topic': '휴가 규정 개정'}")
    print()
    result = graph.invoke({"topic": "휴가 규정 개정"})
    print()
    print("최종 스테이트:")
    for key, value in result.items():
        print(f"  {key}: {value}")
