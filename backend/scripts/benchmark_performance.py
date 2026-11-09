"""Empirical performance benchmarking script for v1.0.0 General Availability.

Measures evaluation runtime, analytics generation, benchmark comparison,
and DAG graph serialization across scales: 10, 100, 1000 evaluations.
"""

import json
import time
import uuid
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.domain.models import CanonicalTrace
from app.services.analytics_service import AnalyticsService
from app.services.benchmark_service import BenchmarkService
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository


def load_fixture_trace(fixture_name: str = "clean_success_trace.json") -> CanonicalTrace:
    fixture_path = Path(__file__).resolve().parent.parent.parent / "fixtures" / fixture_name
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    return CanonicalTrace.model_validate(data)


def run_benchmark():
    # Use SQLite in-memory database with WAL-like speed
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    base_trace = load_fixture_trace()
    scales = [10, 100, 1000]
    results = {}

    for scale in scales:
        print(f"\n================ Running Benchmark Scale N={scale} ================")
        with Session(engine) as session:
            repo = TraceRepository(session)
            eval_service = EvaluationService(session)
            analytics_service = AnalyticsService(session)
            benchmark_service = BenchmarkService(session)

            # 1. Ingestion & Evaluation
            eval_ids = []
            trace_ids = []
            t0 = time.perf_counter()
            for i in range(scale):
                trace_dict = base_trace.model_dump()
                trace_dict["session"]["session_id"] = str(uuid.uuid4())
                trace_dict["workflow"]["workflow_id"] = str(uuid.uuid4())
                trace_dict["session"]["user_intent"] = f"Intent iteration {i}"
                ct = CanonicalTrace.model_validate(trace_dict)
                tr_record = repo.create_trace(ct)
                trace_ids.append(tr_record.trace_id)
                ev_record = eval_service.run_evaluation(tr_record.trace_id)
                eval_ids.append(ev_record.evaluation_id)
            eval_duration = time.perf_counter() - t0

            # 2. Analytics Generation
            t_analytics_start = time.perf_counter()
            analytics_service.get_historical_trends(days=30, limit=scale)
            analytics_duration = time.perf_counter() - t_analytics_start

            # 3. Benchmark Summary Generation
            t_bench_start = time.perf_counter()
            benchmark_service.get_benchmark_summary(limit=scale, offset=0)
            bench_duration = time.perf_counter() - t_bench_start

            # 4. Evaluation Comparison
            t_comp_start = time.perf_counter()
            if len(eval_ids) >= 2:
                benchmark_service.compare_evaluations(eval_ids[0], eval_ids[1])
            comp_duration = time.perf_counter() - t_comp_start

            # 5. Graph Generation
            t_graph_start = time.perf_counter()
            eval_service.get_evaluation_graph(eval_ids[0])
            graph_duration = time.perf_counter() - t_graph_start

            throughput = scale / eval_duration
            avg_eval_ms = (eval_duration / scale) * 1000

            results[scale] = {
                "total_eval_duration_sec": round(eval_duration, 4),
                "avg_eval_ms": round(avg_eval_ms, 2),
                "throughput_evals_per_sec": round(throughput, 1),
                "analytics_gen_sec": round(analytics_duration, 4),
                "benchmark_gen_sec": round(bench_duration, 4),
                "eval_comparison_sec": round(comp_duration, 4),
                "graph_gen_sec": round(graph_duration, 4),
            }

            print(f"Results for N={scale}:")
            print(
                f"  Total Eval Time:     {eval_duration:.3f} s ({avg_eval_ms:.2f} ms/eval, {throughput:.1f} evals/sec)"
            )
            print(f"  Analytics Time:      {analytics_duration * 1000:.2f} ms")
            print(f"  Benchmark Time:      {bench_duration * 1000:.2f} ms")
            print(f"  Graph Time:          {graph_duration * 1000:.2f} ms")

    print("\n================ SUMMARY JSON ================")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run_benchmark()
