# -*- coding: utf-8 -*-
"""통짜 프롬프트 — 모든 요구를 한 번에 (04-4 실습 1).

요구사항 다섯 가지를 프롬프트 하나에 전부 넣고 실행합니다.
결과가 요구를 지켰는지는... 사람이 일일이 세어 봐야 합니다.

준비:
    .env 에 OPENAI_API_KEY 설정

실행:
    uv run python monolithic.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI  # noqa: E402

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,
    api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    temperature=0,
)

TOPIC = "중소 제조기업의 AI 도입"

PROMPT = (
    f"'{TOPIC}'에 대한 짧은 보고서를 작성하세요.\n"
    "요구사항:\n"
    "1. 첫 줄에 보고서 제목\n"
    "2. 핵심 사실 정확히 7개, 번호 목록\n"
    "3. 각 사실은 40자 이내 한 문장\n"
    "4. 각 사실 끝에 근거 유형을 (연구)/(사례)/(통계) 중 하나로 표시\n"
    "5. 목록 뒤에 두 문장 요약\n"
)


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 설정되지 않았습니다.")
        return 1

    msg = llm.invoke(PROMPT)
    print(msg.content)
    print()
    print("-" * 50)
    print("요구사항 5가지를 전부 지켰을까요?")
    print("이 방식에서는 사람이 눈으로 세어 보는 것 말고 확인할 방법이 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
