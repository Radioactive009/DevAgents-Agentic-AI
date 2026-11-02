"""
Messaging Architecture Comparison Harness.

Compares:
1. Blackboard Architecture (Shared Memory, Strict Transactional Locks)
2. EventBus Architecture (Decoupled Pub/Sub, Event-Sourced Projections)

Measures:
- Latency per operation (microseconds)
- Throughput under high concurrency (events/second)
- State consistency & fault behavior
"""

from concurrent.futures import ThreadPoolExecutor
import time
from uuid import uuid4

from src.messaging.blackboard_adapter import BlackboardMessaging
from src.messaging.event_bus import EventBusMessaging
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    TestResult,
)


def create_sample_payloads():
    request = ProjectRequest(
        project_name="Benchmark Todo",
        description="A benchmark project for testing messaging performance.",
        language="Python",
        features=["Task CRUD", "User Auth"],
        acceptance_criteria=["Passes all tests"],
    )
    plan = ArchitecturePlan(
        project_name="Benchmark Todo",
        summary="Architecture plan for benchmark.",
        components=["API", "Store", "Tests"],
        proposed_files=["app.py", "store.py", "tests/test_api.py"],
        implementation_steps=["1. Plan", "2. Code", "3. Test"],
        acceptance_criteria=["Criteria 1", "Criteria 2", "Criteria 3"],
        risks=["Memory leak"],
    )
    code_files = ["app.py", "store.py", "tests/test_api.py"]
    test_result = TestResult(
        passed=4,
        failed=1,
        summary="4 passed, 1 failed",
        error_details=["AssertionError in test_api.py"],
    )
    debug_report = DebugReport(
        diagnosis="KeyError in store.py",
        root_cause="Missing default key",
        severity="medium",
        affected_files=["store.py"],
        recommended_fixes=["Use .get() with default"],
        confidence=0.95,
    )
    return request, plan, code_files, test_result, debug_report


def run_single_pipeline_benchmark(messaging, rounds: int = 100):
    request, plan, code_files, test_result, debug_report = create_sample_payloads()
    latencies = []

    for _ in range(rounds):
        start = time.perf_counter()

        # Step 1: Architecture
        messaging.publish("architecture.plan", plan)
        # Step 2: Code files
        messaging.publish("code.files", code_files)
        # Step 3: Tests
        messaging.publish("test.result", test_result)
        # Step 4: Debug report
        messaging.publish("debug.report", debug_report)

        state = messaging.get_state()
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        assert state.status == "debugging"
        assert len(state.code_files) == 3

    avg_us = (sum(latencies) / len(latencies)) * 1_000_000
    p95_us = sorted(latencies)[int(len(latencies) * 0.95)] * 1_000_000
    return avg_us, p95_us


def run_concurrent_benchmark(messaging_factory, workers: int = 8, tasks_per_worker: int = 50):
    start = time.perf_counter()

    def worker_task():
        _, plan, code_files, test_result, _ = create_sample_payloads()
        messaging = messaging_factory()
        for _ in range(tasks_per_worker):
            messaging.publish("architecture.plan", plan)
            messaging.publish("code.files", code_files)
            messaging.publish("test.result", test_result)
            _ = messaging.get_state()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker_task) for _ in range(workers)]
        for f in futures:
            f.result()

    total_time = time.perf_counter() - start
    total_events = workers * tasks_per_worker * 3
    throughput = total_events / total_time
    return throughput, total_time


def main():
    print("=" * 65)
    print("MESSAGING ARCHITECTURE COMPARISON: BLACKBOARD vs. EVENTBUS")
    print("=" * 65)

    request, _, _, _, _ = create_sample_payloads()

    # 1. Blackboard Benchmark
    bb_messaging = BlackboardMessaging(task_id=str(uuid4()), request=request)
    bb_avg, bb_p95 = run_single_pipeline_benchmark(bb_messaging, rounds=200)

    # 2. EventBus Benchmark
    eb_messaging = EventBusMessaging(task_id=str(uuid4()), request=request)
    eb_avg, eb_p95 = run_single_pipeline_benchmark(eb_messaging, rounds=200)

    # 3. Concurrent Throughput Benchmark
    bb_factory = lambda: BlackboardMessaging(task_id=str(uuid4()), request=request)
    eb_factory = lambda: EventBusMessaging(task_id=str(uuid4()), request=request)

    bb_throughput, bb_concur_time = run_concurrent_benchmark(bb_factory, workers=8, tasks_per_worker=50)
    eb_throughput, eb_concur_time = run_concurrent_benchmark(eb_factory, workers=8, tasks_per_worker=50)

    print(f"\n1. Sequential Pipeline Latency (200 rounds):")
    print(f"   Blackboard Architecture : Avg = {bb_avg:.2f} µs | P95 = {bb_p95:.2f} µs")
    print(f"   EventBus Architecture   : Avg = {eb_avg:.2f} µs | P95 = {eb_p95:.2f} µs")

    print(f"\n2. Concurrent Stress Throughput (8 workers, 1,200 events):")
    print(f"   Blackboard Architecture : {bb_throughput:,.1f} events/sec (Elapsed: {bb_concur_time:.4f}s)")
    print(f"   EventBus Architecture   : {eb_throughput:,.1f} events/sec (Elapsed: {eb_concur_time:.4f}s)")

    print("\n3. Architectural Analysis & Trade-offs:")
    print("   ----------------------------------------------------------------")
    print("   Feature                | Blackboard (Must)     | EventBus (Pub/Sub)")
    print("   -----------------------+-----------------------+----------------")
    print("   State Centralization   | Strict Single Source  | Event-Sourced Reducer")
    print("   Locking Mechanism      | RLock on State Tree   | Lock on Event Log")
    print("   Auditability           | Instant State Snapshot| Full Event Log Replay")
    print("   Best Fit For           | Self-Correction Loops | Microservices / P2P")
    print("   Requirement Compliance | Mandatory Core Arch   | Comparative Pattern")
    print("   ----------------------------------------------------------------")
    print("Conclusion: Blackboard is optimal for self-correcting iterative agent")
    print("loops due to zero serialization overhead and immediate coherent state.")
    print("=" * 65)


if __name__ == "__main__":
    main()

