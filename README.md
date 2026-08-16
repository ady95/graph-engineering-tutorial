# 그래프 엔지니어링 따라하기 — 예제 코드

위키독스 도서 **[그래프 엔지니어링 따라하기](https://wikidocs.net/book/20829)** — AI 협업 조직도를 설계하고 에이전트 경로를 제어하는 실무 가이드 — 의 실습 예제 저장소입니다.

본문의 코드 블록과 같은 내용을 그대로 실행할 수 있는 파일로 정리했습니다. 장별 폴더로 나뉘어 있고, 각 폴더의 `README.md`에 실행 방법과 실측 참고 사항이 있습니다.

## 기준 버전

책은 아래 버전으로 서술했습니다. **버전을 고정해 두는 편을 권합니다** — 예제 출력이 책과 어긋나지 않습니다.

| 패키지 | 버전 |
|---|---|
| Python | 3.12 |
| `langgraph` | 1.2.10 |
| `langchain` | 1.3.14 |
| `langchain-openai` | 1.4.2 |
| `langgraph-cli` | 0.4.31 |
| `langgraph-checkpoint-sqlite` | 3.1.1 |
| `langfuse` | 4.14.3 |

09장(API 서버)에는 `fastapi` 0.141.1, `uvicorn` 0.52.3, `aiosqlite` 0.22.1이 추가됩니다 — `ch09/requirements.txt`에 고정되어 있습니다.

## 시작하기

### 1. 필수 사전 설정 (한국어 Windows)

**Windows에서 한국어 로케일(cp949)을 쓰는 경우 아래 두 가지를 먼저 확인하세요.** 설정하지 않으면 개발 서버가 기동조차 되지 않습니다.

| 환경변수 | 값 | 왜 필요한가 |
|---|---|---|
| `PYTHONUTF8` | `1` | `langgraph dev`가 내부 `openapi.json`을 로케일 인코딩으로 읽어 `UnicodeDecodeError`로 죽습니다 |
| `PYTHONPATH` | (비어 있어야 함) | LibreOffice 등이 등록한 경로가 `resource` 네임스페이스 패키지를 만들어 서버 기동을 깨뜨립니다 |

PowerShell에서 현재 세션에만 적용하려면:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = ""
```

macOS·Linux는 해당하지 않습니다.

### 2. 설치

[uv](https://docs.astral.sh/uv/)를 사용합니다.

```bash
git clone https://github.com/ady95/graph-engineering-tutorial.git
cd graph-engineering-tutorial/ch02

uv venv --python 3.12
uv pip install -r requirements.txt
```

### 3. 환경변수

`.env.example`을 복사해 `.env`로 만들고 값을 채웁니다.

```bash
cp .env.example .env
```

**`.env`에는 ASCII만 쓰세요.** 한글 주석 한 줄로도 개발 서버가 기동 실패합니다 (python-dotenv가 로케일 인코딩으로 읽습니다).

```
OPENAI_API_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com
```

Langfuse는 리전별로 계정과 데이터가 분리됩니다. 한국에서는 JP(도쿄) 리전이 가장 가깝습니다. **리전은 나중에 옮기기 어려우니 처음에 정하세요.**

## 장별 예제

| 폴더 | 장 | 내용 |
|---|---|---|
| [ch02](ch02/) | 02. 개발 환경 구축 | 환경 점검 스크립트, LLM 첫 호출, 최소 그래프, Langfuse 연동 |
| [ch03](ch03/) | 03. 첫 그래프 만들기 | 스테이트 부분 업데이트, 최소 그래프 + Mermaid 시각화, 조사→요약 LLM 그래프 |
| [ch04](ch04/) | 04. 노드 설계 | 규칙 있는/없는 프롬프트 비교, 코드·AI 판정 비교, 통짜 프롬프트 vs 3노드 분할 |
| [ch05](ch05/) | 05. 엣지와 경로 제어 | 라우터+Fallback, 병렬 팬아웃, Send 오케스트레이터-워커, 생성자-평가자 루프, 재귀 한도 실험, interrupt 승인, 다섯 패턴 조립 |
| [ch06](ch06/) | 06. 스테이트와 추적 | 덮어쓰기 vs 리듀서, SqliteSaver 실행 이력, 타임트래블(되감기·상태 수정 분기·부분 재실행) |
| [ch07](ch07/) | 07. 운영 준비 | 노드 timeout + error_handler, RetryPolicy·예산 안전 정지, 모델 배분 A/B, 노드별 비용 측정 |
| [ch08](ch08/) | 08. 기업 업무 적용 | 프로젝트 A: 견적·승인 워크플로우 / 프로젝트 B: 시장 조사 파이프라인 |
| [ch09](ch09/) | 09. 배포와 서비스화 | FastAPI 최소 API, SSE 스트리밍, 인증·한도·영속 체크포인트의 견적 API |
| [ch10](ch10/) | 10. 멀티 에이전트 조직 | 서브그래프(스키마 공유·번역), AI 슈퍼바이저 반복 위임, 3팀 조직 |

## 라이선스

예제 코드는 [MIT 라이선스](LICENSE)입니다. 자유롭게 가져다 쓰세요.

## 도서 정보

- 위키독스: https://wikidocs.net/book/20829
- 이 책은 Claude Code(AI)를 활용해 집필하며, 모든 설치·실습을 실제로 실행해 검증합니다. 각 페이지에 검증 상태와 기준 버전을 표시합니다.

## 정정·제보

예제가 동작하지 않거나 책 내용과 다르면 [Issues](https://github.com/ady95/graph-engineering-tutorial/issues)로 알려주세요. 실행 환경(OS, 파이썬 버전, 패키지 버전)을 함께 적어주시면 확인이 빠릅니다.
