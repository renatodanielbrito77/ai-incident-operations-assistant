from copy import deepcopy
import unittest

from history_rules import match_historical_incidents


class HistoryRulesTest(unittest.TestCase):
    def setUp(self):
        self.message = "Timeout while connecting to payment service"
        self.incident = {
            "historical_incident_id": "HIST-001",
            "application": "checkout",
            "summary": "Timeouts no checkout",
            "symptoms": [self.message, "Latência elevada"],
            "resolution": "Intervenção realizada no passado",
            "observed_result": "Resultado observado no passado",
        }

    def match(self, messages, incidents=None):
        return match_historical_incidents(
            [self.incident] if incidents is None else incidents,
            [{"message": message} for message in messages],
        )

    def test_identical_full_message(self):
        self.assertEqual(self.match([self.message]), [{
            "historical_incident": self.incident,
            "matched_symptoms": [self.message],
        }])

    def test_case_and_edge_whitespace_are_ignored(self):
        self.incident["symptoms"] = [f"  {self.message}\t"]
        self.assertEqual(self.match([f"\n{self.message.upper()}  "]), [{
            "historical_incident": self.incident,
            "matched_symptoms": [f"  {self.message}\t"],
        }])

    def test_similar_or_partial_messages_do_not_match(self):
        for message in (
            "Timeout while connecting to identity service",
            "Timeout while connecting",
            f"ERROR: {self.message}",
        ):
            with self.subTest(message=message):
                self.assertEqual(self.match([message]), [])

    def test_punctuation_accents_and_internal_spaces_are_significant(self):
        for symptom, message in (
            (self.message, f"{self.message}."),
            ("Latência elevada", "Latencia elevada"),
            (self.message, self.message.replace("while connecting", "while  connecting")),
        ):
            with self.subTest(message=message):
                incident = {**self.incident, "symptoms": [symptom]}
                self.assertEqual(self.match([message], [incident]), [])

    def test_unrelated_message(self):
        self.assertEqual(self.match(["Password reset email delivery failed"]), [])

    def test_preserves_all_matching_histories_and_input_order(self):
        second = {**self.incident, "historical_incident_id": "HIST-002"}
        incidents = [second, self.incident]
        self.assertEqual(self.match([self.message], incidents), [
            {"historical_incident": incident, "matched_symptoms": [self.message]}
            for incident in incidents
        ])

    def test_duplicate_logs_do_not_duplicate_matches(self):
        self.assertEqual(
            self.match([self.message, self.message, f" {self.message.upper()} "]),
            self.match([self.message]),
        )

    def test_multiple_symptoms_preserve_symptom_order(self):
        self.assertEqual(self.match(["Latência elevada", self.message]), [{
            "historical_incident": self.incident,
            "matched_symptoms": [self.message, "Latência elevada"],
        }])

    def test_duplicate_symptoms_preserve_first_original_text(self):
        first = f"  {self.message.upper()} "
        self.incident["symptoms"] = [first, self.message, self.message.lower()]
        self.assertEqual(self.match([self.message]), [{
            "historical_incident": self.incident,
            "matched_symptoms": [first],
        }])

    def test_empty_inputs(self):
        self.assertEqual(self.match([self.message], []), [])
        self.assertEqual(self.match([]), [])
        self.assertEqual(self.match([self.message], [
            {**self.incident, "symptoms": []}
        ]), [])

    def test_blank_texts_do_not_match(self):
        self.incident["symptoms"] = ["", "  ", "\t\n"]
        self.assertEqual(self.match(["", " ", "\n\t"]), [])

    def test_nonmatching_history_is_excluded(self):
        unrelated = {**self.incident, "symptoms": ["Outro sintoma"]}
        self.assertEqual(self.match([self.message], [unrelated, self.incident]), [{
            "historical_incident": self.incident,
            "matched_symptoms": [self.message],
        }])

    def test_does_not_mutate_inputs(self):
        incidents = [deepcopy(self.incident)]
        logs = [{"message": f" {self.message.upper()} "}]
        before = deepcopy((incidents, logs))
        match_historical_incidents(incidents, logs)
        self.assertEqual((incidents, logs), before)


if __name__ == "__main__":
    unittest.main()
