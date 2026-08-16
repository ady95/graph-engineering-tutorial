# 10장 — 멀티 에이전트 조직: 서브그래프와 슈퍼바이저

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

`subgraph_demo.py`는 LLM을 호출하지 않으므로 API 키 없이 동작합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `subgraph_demo.py` | 컴파일된 그래프를 노드로 — 스키마 공유/번역 (LLM 없음) | 10-1 |
| `supervisor_demo.py` | AI 슈퍼바이저의 반복 위임 + 상한 | 10-2 |
| `team_org.py` | 조사팀·작성팀·검수팀 3팀 조직 | 10-5 |

## 실행

```bash
uv run python subgraph_demo.py
uv run python supervisor_demo.py
uv run python team_org.py
```

## 실측 참고 (v1.2.10)

- 컴파일된 그래프를 `add_node`에 그대로 넘기면 서브그래프가 됩니다. 부모와 겹치는 스테이트 필드만 오가고, 서브그래프 내부 필드(중간 산출물)는 부모에게 보이지 않습니다 — 격리 실측 확인
- 부모와 어휘(스키마)가 다르면 변환 함수로 감싸 `subgraph.invoke`를 호출합니다
- 슈퍼바이저는 JSON 판단 + 코드 가드(허용 목록·위임 상한) 조합으로 구현했습니다. 실측에서 조사 → 작성 → 완료를 3회 위임으로 정확히 지휘했습니다
- 팀별로 다른 모델을 씁니다: 조사팀 luna / 작성팀 terra / 검수팀 코드($0)
