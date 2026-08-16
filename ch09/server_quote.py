# -*- coding: utf-8 -*-
"""견적 워크플로우를 사내 API로 (09-4, 09-5, 09-7).

08장의 견적 그래프를 서비스로 포장한 것입니다.
- 견적 건마다 thread_id 로 상태가 분리되고 (09-4)
- SqliteSaver 라서 서버를 껐다 켜도 승인 대기가 유지되며 (09-4)
- API 키 인증과 사용 한도가 걸려 있습니다 (09-5)

실행:
    uv run uvicorn server_quote:app --port 8092

호출 예:
    curl -X POST http://127.0.0.1:8092/quotes \
         -H "Content-Type: application/json" -H "X-API-Key: team-sales-01" \
         -d '{"고객명":"한빛물류","요청내용":"재고 문의 챗봇","규모":"중","납기":"10월 말"}'
    curl -X POST http://127.0.0.1:8092/quotes/{thread_id}/decision \
         -H "Content-Type: application/json" -H "X-API-Key: team-sales-01" \
         -d '{"decision": "승인"}'
"""
import os
import uuid
from contextlib import asynccontextmanager
from typing import Literal, TypedDict

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


# ── 그래프 (08-6의 견적 워크플로우 축약판) ─────────────────────
def make_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
        temperature=0,
    )


small_llm = make_llm(os.environ.get("OPENAI_MODEL_SMALL", "gpt-5.6-luna"))
large_llm = make_llm(os.environ.get("OPENAI_MODEL_LARGE", "gpt-5.6-terra"))

PRICE_TABLE = {"챗봇구축": 8_000_000, "데이터분석": 5_000_000, "유지보수": 1_500_000}
SCALE_MULTIPLIER = {"소": 1.0, "중": 1.8, "대": 3.0}


class QuoteState(TypedDict):
    request: dict
    service_type: str
    price: int
    quote_doc: str
    decision: str
    status: str


async def classify(state: QuoteState) -> dict:
    msg = await small_llm.ainvoke(
        "다음 요청을 챗봇구축/데이터분석/유지보수 중 하나로 분류하세요. "
        "확신이 없으면 '기타'. 해당 단어만 답하세요.\n"
        f"요청: {state['request']['요청내용']}"
    )
    return {"service_type": msg.content.strip()}


def route_classify(state: QuoteState) -> Literal["calculate", "manual"]:
    return "calculate" if state["service_type"] in PRICE_TABLE else "manual"


def calculate(state: QuoteState) -> dict:
    base = PRICE_TABLE[state["service_type"]]
    return {"price": int(base * SCALE_MULTIPLIER.get(state["request"]["규모"], 1.0))}


async def compose(state: QuoteState) -> dict:
    msg = await large_llm.ainvoke(
        f"고객 {state['request']['고객명']} 님께 보낼 {state['service_type']} 견적서 본문을 쓰세요. "
        f"금액 {state['price']:,}원(부가세 별도)과 납기 {state['request']['납기']}, "
        "'유효기간 30일' 문구를 포함해 4문장 이내."
    )
    return {"quote_doc": msg.content.strip()}


def approval(state: QuoteState) -> dict:
    decision = interrupt(
        {
            "질문": "이 견적서를 발송할까요?",
            "고객": state["request"]["고객명"],
            "금액": f"{state['price']:,}원",
            "견적서": state["quote_doc"],
        }
    )
    return {"decision": decision}


def route_decision(state: QuoteState) -> Literal["send", "manual"]:
    return "send" if state["decision"] == "승인" else "manual"


def send(state: QuoteState) -> dict:
    return {"status": f"발송 완료 — {state['price']:,}원"}


def manual(state: QuoteState) -> dict:
    return {"status": "담당자 검토로 전환"}


builder = StateGraph(QuoteState)
for name, fn in [("classify", classify), ("calculate", calculate), ("compose", compose),
                 ("approval", approval), ("send", send), ("manual", manual)]:
    builder.add_node(name, fn)
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route_classify, {"calculate": "calculate", "manual": "manual"})
builder.add_edge("calculate", "compose")
builder.add_edge("compose", "approval")
builder.add_conditional_edges("approval", route_decision, {"send": "send", "manual": "manual"})
builder.add_edge("send", END)
builder.add_edge("manual", END)

# 파일 기반 체크포인터 — 서버를 재시작해도 승인 대기 건이 살아 있다.
# 주의 1: 비동기 서버에서는 SqliteSaver가 아니라 AsyncSqliteSaver를 써야 한다.
#         (SqliteSaver로 ainvoke하면 NotImplementedError — 실측)
# 주의 2: AsyncSqliteSaver는 실행 중인 이벤트 루프가 필요해서
#         모듈 수준이 아니라 lifespan 안에서 만들어야 한다. (RuntimeError — 실측)
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    async with AsyncSqliteSaver.from_conn_string("quotes.sqlite") as saver:
        graph = builder.compile(checkpointer=saver)  # 기동 시 한 번 컴파일
        yield


# ── 인증과 사용 한도 (09-5) ────────────────────────────────────
API_KEYS = {"team-sales-01": "영업1팀", "team-sales-02": "영업2팀"}  # 실무: DB/시크릿 저장소
DAILY_LIMIT = int(os.environ.get("QUOTE_DAILY_LIMIT", "100"))
usage_count: dict[str, int] = {}


async def require_key(x_api_key: str = Header(default="")) -> str:
    """모든 엔드포인트가 의존하는 인증 관문."""
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키")
    usage_count[x_api_key] = usage_count.get(x_api_key, 0) + 1
    if usage_count[x_api_key] > DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="일일 사용 한도 초과 — 관리자에게 문의")
    return x_api_key


# ── API (09-4, 09-7) ──────────────────────────────────────────
app = FastAPI(title="견적 API", version="1.0", lifespan=lifespan)


class QuoteRequest(BaseModel):
    고객명: str = Field(min_length=1)
    요청내용: str = Field(min_length=5)
    규모: Literal["소", "중", "대"]
    납기: str = Field(min_length=1)


class DecisionRequest(BaseModel):
    decision: Literal["승인", "반려"]


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/quotes")
async def create_quote(req: QuoteRequest, key: str = Depends(require_key)) -> dict:
    """견적 건을 시작한다 — 승인 지점에서 멈추고 대기 정보를 돌려준다."""
    thread_id = f"quote-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke({"request": req.model_dump()}, config)

    if "__interrupt__" in result:
        return {"thread_id": thread_id, "status": "승인 대기",
                "pending": result["__interrupt__"][0].value, "요청팀": API_KEYS[key]}
    return {"thread_id": thread_id, "status": result["status"]}


@app.post("/quotes/{thread_id}/decision")
async def decide(thread_id: str, req: DecisionRequest, key: str = Depends(require_key)) -> dict:
    """멈춰 있는 견적 건에 사람의 결정을 넣어 재개한다."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="대기 중인 승인이 없는 건입니다")
    result = await graph.ainvoke(Command(resume=req.decision), config)
    return {"thread_id": thread_id, "decision": req.decision, "status": result["status"]}
