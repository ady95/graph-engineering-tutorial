# -*- coding: utf-8 -*-
"""스트리밍 응답 — 노드 진행 상황을 실시간으로 (09-3).

실행:
    uv run uvicorn server_stream:app --port 8091

호출 (-N: 버퍼링 없이 도착 즉시 출력):
    curl -N -X POST http://127.0.0.1:8091/research/stream \
         -H "Content-Type: application/json" \
         -d '{"topic": "전기차 배터리 재활용"}'
"""
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from graph_def import graph

app = FastAPI(title="조사 API (스트리밍)", version="1.0")


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


def sse(event: str, data: dict) -> str:
    """SSE 한 건의 전송 형식: event 줄 + data 줄 + 빈 줄."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/research/stream")
async def run_research_stream(req: ResearchRequest) -> StreamingResponse:
    """노드가 하나 끝날 때마다 진행 상황을 흘려보낸다."""

    async def event_stream():
        yield sse("start", {"topic": req.topic})
        # stream_mode="updates": 노드가 끝날 때마다 {노드 이름: 갱신분}이 나온다
        async for update in graph.astream({"topic": req.topic}, stream_mode="updates"):
            for node_name, changed in update.items():
                yield sse("node_done", {
                    "node": node_name,
                    "fields": list(changed.keys()),
                    "preview": str(list(changed.values())[0])[:60],
                })
        yield sse("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
