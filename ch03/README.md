# 03장 — 첫 그래프 만들기

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

`state_demo.py`와 `graph_minimal.py`는 LLM을 호출하지 않으므로 API 키 없이 동작합니다. `research_summary.py`만 `OPENAI_API_KEY`가 필요합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `state_demo.py` | 스테이트 부분 업데이트 확인 (LLM 없음) | 03-2 |
| `graph_minimal.py` | 최소 그래프 — 노드 2개, 코드 해설용 (LLM 없음) | 03-3 |
| `research_summary.py` | 조사 → 요약 그래프, 노드 속이 진짜 LLM | 03-4 |
| `langgraph.json` | 개발 서버 설정 (Studio에서 열 때) | 03-4 |

## 실행

```bash
# 스테이트 부분 업데이트 관찰
uv run python state_demo.py

# 최소 그래프 + Mermaid 구조 출력
uv run python graph_minimal.py

# 조사 → 요약 LLM 그래프 (OPENAI_API_KEY 필요)
uv run python research_summary.py

# 개발 서버로 열기 (선택)
uv run langgraph dev
```
