# 05장 — 엣지와 경로 제어

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

`loop_runaway.py`와 `approval_graph.py`는 LLM을 호출하지 않으므로 API 키 없이 동작합니다. 나머지는 `OPENAI_API_KEY`가 필요합니다.

## 파일

| 파일 | 패턴 | 관련 절 |
|---|---|---|
| `router_graph.py` | 패턴 1: 라우터 + Fallback | 05-1, 05-2 |
| `parallel_graph.py` | 패턴 2: 병렬 팬아웃 (순차와 시간 비교) | 05-3 |
| `orchestrator_workers.py` | 패턴 3: 오케스트레이터-워커 (Send) | 05-4 |
| `maker_checker.py` | 패턴 4: 생성자-평가자 루프 | 05-5 |
| `loop_runaway.py` | 상한 없는 루프 vs 상한 3회 (LLM 없음) | 05-6 |
| `approval_graph.py` | 패턴 5: interrupt 승인 (LLM 없음) | 05-7 |
| `assemble_graph.py` | 다섯 패턴 조립 | 05-8 |
| `langgraph.json` | 개발 서버 설정 | — |

## 실행

```bash
uv run python router_graph.py
uv run python parallel_graph.py
uv run python orchestrator_workers.py
uv run python maker_checker.py
uv run python loop_runaway.py
uv run python approval_graph.py
uv run python assemble_graph.py
```

## 실측 참고 (v1.2.10)

- 라우팅 함수가 매핑에 없는 값을 반환하면 실행 시점에 `KeyError`로 죽습니다 — Fallback 레이블을 반드시 매핑에 포함하세요.
- 리듀서 없이 두 노드가 같은 필드에 동시에 쓰면 `InvalidUpdateError`가 납니다 — 병렬 대상 필드는 `Annotated[list, operator.add]`로 선언하세요.
- 이 버전의 기본 재귀 한도는 **10007단계**입니다 (`LANGGRAPH_DEFAULT_RECURSION_LIMIT`로 변경 가능). 기본값을 안전망으로 믿지 말고 재시도 상한을 직접 두세요.
