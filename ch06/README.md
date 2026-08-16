# 06장 — 스테이트와 실행 경로 추적

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

`state_rules.py`와 `checkpoint_graph.py`는 LLM을 호출하지 않으므로 API 키 없이 동작합니다. `time_travel.py`만 `OPENAI_API_KEY`가 필요합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `state_rules.py` | 덮어쓰기 vs 리듀서 누적 (LLM 없음) | 06-2 |
| `checkpoint_graph.py` | SqliteSaver + 실행 이력 조회 (LLM 없음) | 06-3 |
| `time_travel.py` | 되감기·상태 수정 분기·부분 재실행 | 06-4 |

## 실행

```bash
uv run python state_rules.py
uv run python checkpoint_graph.py
uv run python time_travel.py
```

실행하면 폴더에 `checkpoints.sqlite` / `time_travel.sqlite` 파일이 생깁니다 (gitignore 대상). 지우면 이력이 초기화됩니다.
