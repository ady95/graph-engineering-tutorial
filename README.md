# 그래프 엔지니어링 따라하기 — 예제 코드

위키독스 도서 **[그래프 엔지니어링 따라하기](https://wikidocs.net/book/20829)** — AI 협업 조직도를 설계하고 에이전트 경로를 제어하는 실무 가이드 — 의 실습 예제 저장소입니다.

> 집필 중입니다. 책이 진행되는 대로 장별 예제가 추가됩니다.

본문의 코드 블록과 같은 내용을 그대로 실행할 수 있는 파일로 정리했습니다. 장별 폴더로 나뉘어 있고, 각 폴더의 `README.md`에 실행 방법이 있습니다.

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
| [ch02](ch02/) | 02. 개발 환경 구축 | 환경 점검 스크립트, 최소 그래프, 개발 서버 설정 |

이후 장은 집필 진행에 따라 추가됩니다.

## 라이선스

예제 코드는 [MIT 라이선스](LICENSE)입니다. 자유롭게 가져다 쓰세요.

## 도서 정보

- 위키독스: https://wikidocs.net/book/20829
- 이 책은 Claude Code(AI)를 활용해 집필하며, 모든 설치·실습을 실제로 실행해 검증합니다. 각 페이지에 검증 상태와 기준 버전을 표시합니다.

## 정정·제보

예제가 동작하지 않거나 책 내용과 다르면 [Issues](https://github.com/ady95/graph-engineering-tutorial/issues)로 알려주세요. 실행 환경(OS, 파이썬 버전, 패키지 버전)을 함께 적어주시면 확인이 빠릅니다.
