# -*- coding: utf-8 -*-
"""실습: 노드별 비용·지연 표 만들기 (07-4).

최근 트레이스들을 Langfuse API로 조회해
실행별 · LLM 호출별 모델/토큰/비용/지연을 표로 출력합니다.
model_mix.py 를 먼저 실행해 두세요.

준비:
    .env 에 LANGFUSE_PUBLIC_KEY / SECRET_KEY / BASE_URL 설정

실행:
    uv run python measure_costs.py
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client  # noqa: E402


def main() -> int:
    api = get_client().api

    traces = api.trace.list(limit=2)  # 최근 2건 = model_mix의 B안, A안
    if not traces.data:
        print("트레이스가 없습니다. model_mix.py 를 먼저 실행하세요.")
        return 1

    for trace in traces.data:
        tags = ", ".join(trace.tags or [])
        print(f"== 실행: {tags or trace.id[:8]} ==")
        print(f"   전체 지연 {trace.latency:.2f}초 / 총비용 ${trace.total_cost:.6f}")

        detail = api.trace.get(trace.id)
        gens = [o for o in detail.observations if o.type == "GENERATION"]
        spans = {o.id: o.name for o in detail.observations}
        for g in sorted(gens, key=lambda x: x.start_time):
            node = spans.get(g.parent_observation_id, "?")
            latency = (g.end_time - g.start_time).total_seconds()
            cost = float(g.calculated_total_cost or 0)
            print(
                f"   - 노드 {node:<10} 모델 {g.model:<14} "
                f"토큰 {g.usage.input:>4}/{g.usage.output:<4} "
                f"비용 ${cost:.6f}  지연 {latency:.2f}초"
            )
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
