# 09장 — 그래프를 서비스로: 배포와 서비스화

02장 기준 버전에 API 서버 패키지가 추가됩니다. 한국어 Windows는 02장의 필수 사전 설정(`PYTHONUTF8=1`, `PYTHONPATH` 비우기)을 먼저 확인하세요.

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt   # fastapi / uvicorn / aiosqlite 포함
cp .env.example .env
```

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `graph_def.py` | 서버에 얹을 그래프 (비동기 노드) | 09-2, 09-3 |
| `server_basic.py` | 최소 API 서버 | 09-2 |
| `server_stream.py` | SSE 스트리밍 서버 | 09-3 |
| `server_quote.py` | 견적 API — 인증·한도·영속 체크포인트·승인 재개 | 09-4, 09-5, 09-7 |

## 실행

```bash
uv run uvicorn server_basic:app --port 8090
uv run uvicorn server_stream:app --port 8091
uv run uvicorn server_quote:app --port 8092
```

호출 예시는 각 파일 상단 docstring에 있습니다. Windows 콘솔에서 한글 JSON을 -d 인자로 직접 넘기면 인코딩이 깨질 수 있으니, 파일로 저장해 `--data-binary @file`로 보내세요.

## 실측 참고 (v1.2.10 · fastapi 0.141.1 · uvicorn 0.52.3)

- **비동기 서버에서는 SqliteSaver가 아니라 AsyncSqliteSaver**를 써야 합니다. SqliteSaver로 `ainvoke`하면 `NotImplementedError`가 납니다 (실측)
- **AsyncSqliteSaver는 실행 중인 이벤트 루프가 필요**해 모듈 수준에서 만들면 `RuntimeError: no running event loop`가 납니다. FastAPI의 lifespan 안에서 `from_conn_string` 컨텍스트로 만드세요 (실측, server_quote.py 참고)
- 재시작 영속성 실측: 승인 대기 상태에서 서버 프로세스를 종료·재기동한 뒤, 같은 thread_id로 decision을 보내면 저장된 지점부터 재개되어 정상 완료됩니다
- 사용 한도 실측: 한도 3으로 설정 시 4번째 호출에서 429 반환
