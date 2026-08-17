# 02장 — 개발 환경 구축

## 필수 사전 설정 (한국어 Windows)

두 환경변수를 먼저 확인하세요. 설정하지 않으면 개발 서버가 기동 실패합니다. macOS·Linux는 해당하지 않습니다.

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = ""
```

| 환경변수 | 왜 필요한가 |
|---|---|
| `PYTHONUTF8=1` | `langgraph dev`가 내부 `openapi.json`을 로케일 인코딩으로 읽어 `UnicodeDecodeError: 'cp949'`로 죽습니다 |
| `PYTHONPATH` 비우기 | LibreOffice 등이 등록한 경로가 `resource` 네임스페이스 패키지를 만들어 `AttributeError: module 'resource' has no attribute 'getpagesize'`가 발생합니다 |

## 설치

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
```

`requirements.txt`의 패키지는 **한 번에 함께** 설치하세요. 나눠서 설치하면 `langgraph-api` 해석 버전이 달라져 End of Life 경고가 뜹니다.

## 환경변수

```bash
cp .env.example .env
```

`.env`는 **UTF-8로 저장**하고 한글 주석은 넣지 마세요. `load_dotenv()`는 UTF-8로 읽지만 `langgraph dev`는 로케일 인코딩(cp949)으로 읽어 기동이 실패할 수 있습니다. `PYTHONUTF8=1`로도 해결됩니다.

이 장의 예제는 LLM을 호출하지 않으므로 API 키 없이도 전부 동작합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `check_env.py` | 환경 점검 — 파이썬·패키지·임포트·환경변수 4단계 확인 | 02-9 |
| `first_call.py` | LLM 첫 호출 — 응답·토큰·비용 확인 | 02-4 |
| `graph.py` | 최소 그래프 (조사 → 요약 2노드) | 02-5, 02-6 |
| `graph_traced.py` | Langfuse 추적을 붙인 그래프 (검증 노드 추가) | 02-7 |
| `langgraph.json` | 개발 서버 설정 | 02-5 |
| `requirements.txt` | 기준 버전 고정 | 02-3 |

## 실행

```bash
# 환경 점검
uv run python check_env.py

# 그래프 단독 실행
uv run python graph.py

# 개발 서버 (Studio 연결)
uv run langgraph dev

# LLM 첫 호출 (OPENAI_API_KEY 필요)
uv run python first_call.py

# Langfuse 추적 확인 (LANGFUSE_* 환경변수 필요)
uv run python graph_traced.py
```

## OpenAI 호환 서버를 쓰는 경우

`OPENAI_BASE_URL`만 채우면 됩니다. 자체 호스팅 서버, 게이트웨이, 로컬 추론 서버 모두 같습니다.

```python
llm = ChatOpenAI(
    model=os.environ["OPENAI_MODEL"],
    base_url=os.environ.get("OPENAI_BASE_URL") or None,  # 비우면 공식 API
    api_key=os.environ["OPENAI_API_KEY"],
)
```

책 본문은 공식 OpenAI API 기준으로 서술합니다. 예제 코드는 두 경우 모두 동작합니다.

## Langfuse 연동에 관해

추적을 붙이는 코드는 사실상 한 줄입니다. LangGraph 전용 설정은 없고 LangChain 콜백 방식을 그대로 씁니다.

```python
from langfuse.langchain import CallbackHandler

handler = CallbackHandler()
graph.invoke(state, config={"callbacks": [handler]})
```

- **리전마다 계정과 데이터가 분리됩니다.** 키를 발급받은 리전과 `LANGFUSE_BASE_URL`이 같아야 합니다. 나중에 옮기려면 새 계정을 만들어 데이터를 이관해야 하므로 처음에 정하세요.
- 짧게 끝나는 스크립트는 전송 전에 프로세스가 종료될 수 있습니다. `langfuse.flush()`를 호출하세요.
- 트레이스가 화면에 반영되기까지 10초 정도 걸립니다.
- **LLM을 호출하지 않는 코드 전용 노드도 트레이스에 그대로 보입니다** (Langfuse 4.14.3 실측). 별도 설정이 필요하지 않습니다.

개발 서버가 뜨면 출력에 표시되는 Studio UI 주소로 접속합니다. Docker가 필요 없고 LangSmith 계정도 필요하지 않습니다.

## 실행 결과 예시

`check_env.py`:

```
========================================================
 그래프 엔지니어링 환경 점검
========================================================

[1] 파이썬
    파이썬 3.12.9

[2] 패키지 버전
    패키지                            기준         설치됨        상태
    langgraph                      1.2.10     1.2.10     OK
    langchain                      1.3.14     1.3.14     OK
    ...

[3] 임포트 확인
    langgraph.graph                            OK
    ...

 점검 통과 — 다음 장으로 진행할 수 있습니다
========================================================
```

`graph.py`:

```
topic: 그래프 엔지니어링
collected: '그래프 엔지니어링'에 대해 수집한 자료 3건
summary: [요약] '그래프 엔지니어링'에 대해 수집한 자료 3건
```

## 주의

- 서버 로그를 **이 폴더 안에 저장하지 마세요.** 핫 리로드가 파일 변경을 감지해 무한 반복됩니다.
- 서버는 **Ctrl+C로 정상 종료**하세요. 강제 종료하면 `multiprocessing`으로 뜬 자식 프로세스가 남아 `.venv`를 잠급니다.
