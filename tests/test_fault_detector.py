"""Unit tests for Fault Detection Engine."""

from assurance_engine.fault_detector import FaultDetector


def test_detect_all_5_fault_benchmarks():
    detector = FaultDetector({})
    benchmarks = detector.run_all_benchmarks()
    assert len(benchmarks) == 5
    f_ids = {b.id for b in benchmarks}
    assert f_ids == {"F1", "F2", "F3", "F4", "F5"}
    for b in benchmarks:
        assert b.status == "DETECTED"
        assert len(b.corrective_action) > 0
        assert len(b.potential_impact) > 0
        assert len(b.detected_evidence) > 0

