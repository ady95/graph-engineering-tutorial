# 08장 — 기업 업무에 적용하기

02장과 같은 기준 버전을 씁니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

두 프로젝트 모두 `OPENAI_API_KEY`가 필요합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `quote_workflow.py` | 프로젝트 A: 견적·승인 워크플로우 (8노드, AI 2개) | 08-6 |
| `research_pipeline.py` | 프로젝트 B: 시장 조사 보고서 파이프라인 (병렬+재조사 루프) | 08-7 |

## 실행

```bash
uv run python quote_workflow.py
uv run python research_pipeline.py
```

## 설계 메모

- 프로젝트 A: 노드 8개 중 AI는 classify(최소 모델)·compose(상위 모델) 둘뿐. 나머지는 코드와 사람 — 건당 비용 $0.0013 수준 (실측)
- 프로젝트 B: 병렬 조사 노드들이 **서로 다른 필드에 쓰므로 리듀서가 필요 없고**, 재조사 루프에서 자연스럽게 덮어쓰기가 됩니다. 병렬 루프백의 출발점으로 kickoff 코드 노드를 두는 패턴 참고
- 두 프로젝트 모두 interrupt 승인을 포함하므로 체크포인터(InMemorySaver)로 컴파일합니다. 운영에서는 SqliteSaver 이상으로 교체하세요 (06-3)
