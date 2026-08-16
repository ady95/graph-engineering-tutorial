# -*- coding: utf-8 -*-
"""FastAPI에 그래프 얹기 — 최소 API 서버 (09-2).

실행:
    uv run uvicorn server_basic:app --port 8090

호출:
    curl -X POST http://127.0.0.1:8090/research \
         -H "Content-Type: application/json" \
         -d '{"topic": "전기차 배터리 재활용"}'
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from graph_def import graph

app = FastAPI(title="조사 API", version="1.0")


class ResearchRequest(BaseModel):
    """요청 본문 — Pydantic이 형식을 검증한다."""

    topic: str = Field(min_length=2, max_length=200, description="조사 주제")


class ResearchResponse(BaseModel):
    """응답 — 스테이트에서 돌려줄 것만 고른다."""

    topic: str
    research: str
    summary: str


@app.get("/health")
async def health() -> dict:
    """헬스체크 — 서버와 그래프가 살아 있는지."""
    return {"ok": True, "graph": "research_summary"}


@app.post("/research", response_model=ResearchResponse)
async def run_research(req: ResearchRequest) -> ResearchResponse:
    """그래프를 한 번 실행하고 최종 스테이트를 돌려준다."""
    try:
        result = await graph.ainvoke({"topic": req.topic})
    except Exception as exc:  # LLM 장애 등 — 원인은 로그로, 고객에겐 502로
        raise HTTPException(status_code=502, detail=f"그래프 실행 실패: {type(exc).__name__}")
    return ResearchResponse(**{k: result[k] for k in ("topic", "research", "summary")})
