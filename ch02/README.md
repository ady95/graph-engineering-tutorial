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

`.env`에는 **ASCII만** 쓰세요. 한글 주석 한 줄로도 개발 서버가 기동 실패합니다.

이 장의 예제는 LLM을 호출하지 않으므로 API 키 없이도 전부 동작합니다.

## 파일

| 파일 | 용도 | 관련 절 |
|---|---|---|
| `check_env.py` | 환경 점검 — 파이썬·패키지·임포트·환경변수 4단계 확인 | 02-9 |
| `graph.py` | 최소 그래프 (조사 → 요약 2노드) | 02-5, 02-6 |
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
```

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
