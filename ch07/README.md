# 07장 — 운영 준비: 신뢰성과 비용

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

`timeout_demo.py`와 `retry_demo.py`는 LLM을 호출하지 않으므로 API 키 없이 동작합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `timeout_demo.py` | 노드 timeout + error_handler (LLM 없음) | 07-1 |
| `retry_demo.py` | RetryPolicy·retry_on·예산 안전 정지 (LLM 없음) | 07-2 |
| `model_mix.py` | 모델 배분 A/B 실행 (최소 vs 상위 모델) | 07-3, 07-4 |
| `measure_costs.py` | Langfuse API로 노드별 비용·지연 표 출력 | 07-4 |

## 실행

```bash
uv run python timeout_demo.py
uv run python retry_demo.py
uv run python model_mix.py        # OPENAI_API_KEY 필요
uv run python measure_costs.py   # LANGFUSE_* 필요, model_mix 실행 후
```

## 실측 참고 (v1.2.10)

- 노드 `timeout`은 **비동기(async) 노드에서만** 동작합니다. 동기 노드는 안전하게 중단할 수 없습니다.
- `error_handler`는 실패 시점의 스테이트를 받아 갱신값 또는 `Command(update=..., goto=...)`를 반환합니다. Command를 쓰면 실패를 기록하면서 대체 경로로 보낼 수 있습니다.
- 모델 배분 실측: 분류 노드를 상위 모델에서 최소 모델로 바꾸면 해당 노드 비용 1/10, 지연 절반, 분류 결과 동일 (이 예제 기준).
- 모델명은 `OPENAI_MODEL_SMALL` / `OPENAI_MODEL_LARGE` 환경변수로 바꿀 수 있습니다.
