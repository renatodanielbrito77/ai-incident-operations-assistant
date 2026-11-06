from copy import deepcopy
import unittest

from temporal_rules import assess_temporal, parse_timestamp, validate_window


class TemporalRulesTest(unittest.TestCase):
    def setUp(self):
        self.incident = dict(window_start="2026-11-04T10:00:00Z", window_end="2026-11-04T10:10:00Z")
        self.monitoring = dict(timestamp="2026-11-04T10:05:00Z")

    def entry(self, timestamp, message="timeout"):
        return dict(timestamp=timestamp, level="ERROR", message=message, provenance={"unchanged": True})

    def test_equivalent_offsets_and_both_inclusive_boundaries(self):
        logs = [self.entry("2026-11-04T07:00:00-03:00"), self.entry("2026-11-04T11:10:00+01:00")]
        metrics = {"timestamp": "2026-11-04T05:00:00-05:00"}
        result = assess_temporal(self.incident, metrics, logs)
        self.assertEqual(result["assessment"]["monitoring_applicability"], "within_window")
        self.assertEqual(result["applicable_log_entries"], logs)
        self.assertEqual(parse_timestamp(logs[0]["timestamp"]), parse_timestamp(self.incident["window_start"]))

    def test_metric_end_boundary_and_single_instant_window(self):
        self.assertEqual(assess_temporal(self.incident, {"timestamp": self.incident["window_end"]}, [self.entry(self.incident["window_end"])])["assessment"]["monitoring_applicability"], "within_window")
        incident = {**self.incident, "window_end": self.incident["window_start"]}
        self.assertEqual(assess_temporal(incident, {"timestamp": incident["window_start"]}, [self.entry(incident["window_start"])])["assessment"]["log_status"], "usable")

    def test_mixed_logs_preserve_order_metadata_and_input(self):
        logs = [self.entry("2026-11-03T10:02:00Z", "old"), self.entry("2026-11-04T10:03:00Z", " current "), self.entry("2026-11-04T10:04:00Z", " \t"), self.entry("2026-11-04T10:11:00Z", "future")]
        original = deepcopy(logs)
        result = assess_temporal(self.incident, self.monitoring, logs)
        self.assertEqual(result["applicable_log_entries"], [logs[1]])
        self.assertEqual([r["temporal_status"] for r in result["assessment"]["log_applicability"]], ["outside_window", "within_window", "within_window", "outside_window"])
        self.assertEqual(logs, original)
        result["applicable_log_entries"][0]["provenance"]["unchanged"] = False
        self.assertEqual(logs, original)

    def test_only_old_messages(self):
        result = assess_temporal(self.incident, self.monitoring, [self.entry("2026-11-03T10:02:00Z"), self.entry(self.incident["window_start"], " ")])
        self.assertEqual(result["assessment"]["log_status"], "LOGS_OUTSIDE_WINDOW")
        self.assertEqual(result["applicable_log_entries"], [])

    def test_empty_and_blank_messages(self):
        for logs in ([], [self.entry(self.incident["window_start"], " \t\n")]):
            with self.subTest(logs=logs):
                self.assertEqual(assess_temporal(self.incident, self.monitoring, logs)["assessment"]["log_status"], "NO_LOG_MESSAGE")

    def test_invalid_naive_or_non_string_timestamps(self):
        for value in ("2026-11-04T10:00:00", "2026-13-04T10:00:00Z", "2026-11-04", "2026-11-04T10:00:00+99:00", "", None, 123, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_timestamp(value)

    def test_reversed_window_accounts_for_offsets(self):
        with self.assertRaises(ValueError):
            validate_window("2026-11-04T10:00:00Z", "2026-11-04T10:30:00+01:00")

    def test_old_metric_is_retained_and_not_a_window_expansion(self):
        metrics = {"timestamp": "2026-11-03T10:05:00Z"}
        original = deepcopy((self.incident, metrics))
        result = assess_temporal(self.incident, metrics, [self.entry(self.incident["window_start"])])
        self.assertEqual(result["assessment"]["monitoring_applicability"], "outside_window")
        self.assertEqual(result["assessment"]["monitoring_timestamp"], metrics["timestamp"])
        self.assertEqual((self.incident, metrics), original)


if __name__ == "__main__":
    unittest.main()
