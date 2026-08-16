# 04장 — 노드 설계

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

이 장의 예제는 전부 LLM을 호출하므로 `OPENAI_API_KEY`가 필요합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `rules_demo.py` | 규칙 없는/있는 프롬프트 비교 + 코드 검증 | 04-2 |
| `three_ways.py` | 같은 판정을 코드·AI로 구현해 비교 | 04-3 |
| `monolithic.py` | 통짜 프롬프트 — 요구 5가지를 한 번에 | 04-4 |
| `split_graph.py` | 3노드 분할: collect(AI) → verify(코드) → compose(AI) | 04-4 |
| `langgraph.json` | 개발 서버 설정 (Studio에서 열 때) | 04-4 |

## 실행

```bash
uv run python rules_demo.py
uv run python three_ways.py
uv run python monolithic.py
uv run python split_graph.py
```

## 참고 — 구조화 출력에 관해

이 장의 예제는 "JSON으로만 답하라"는 지시 + `json.loads` + 코드 검증 방식을 씁니다. 어떤 OpenAI 호환 엔드포인트에서도 동작하기 때문입니다. 공식 OpenAI API를 쓴다면 `llm.with_structured_output(PydanticModel)`로 스키마 강제를 더 편하게 할 수 있습니다 — 단 tool calling을 지원하지 않는 호환 서버에서는 동작하지 않습니다.
