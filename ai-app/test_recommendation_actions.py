from copy import deepcopy
import unittest

from recommendation_rules import validate_candidate_action, validate_candidate_references


class RecommendationActionsTest(unittest.TestCase):
    def assert_unknown(self, candidate):
        self.assertEqual(validate_candidate_action(candidate), {
            "allowed": False,
            "validation_code": "UNKNOWN_ACTION_TYPE",
        })

    def test_observe_is_allowed(self):
        self.assertEqual(validate_candidate_action({"action_type": "observe"}), {
            "allowed": True,
            "validation_code": "ACTION_TYPE_ALLOWED",
        })

    def test_request_verification_is_allowed(self):
        self.assertEqual(validate_candidate_action({"action_type": "request_verification"}), {
            "allowed": True,
            "validation_code": "ACTION_TYPE_ALLOWED",
        })

    def test_environment_change_is_forbidden(self):
        self.assertEqual(validate_candidate_action({"action_type": "change_environment"}), {
            "allowed": False,
            "validation_code": "ACTION_TYPE_FORBIDDEN",
        })

    def test_missing_action_type_is_unknown(self):
        self.assert_unknown({"text": "Texto manual", "cited_chunk_ids": []})

    def test_unknown_empty_and_unnormalized_strings_are_rejected(self):
        for value in ("", " ", "restart", "OBSERVE", " observe", "observe ", "Request_verification"):
            with self.subTest(value=value):
                self.assert_unknown({"action_type": value})

    def test_nonstring_values_are_rejected_without_exceptions(self):
        for value in ([], ["observe"], {}, {"action_type": "observe"}, 0, 1, 0.5, True, False, None):
            with self.subTest(value=value, value_type=type(value).__name__):
                self.assert_unknown({"action_type": value})

    def test_contradictory_text_is_not_interpreted(self):
        self.assertEqual(validate_candidate_action({
            "text": "Reiniciar automaticamente o checkout.",
            "action_type": "observe",
        }), {
            "allowed": True,
            "validation_code": "ACTION_TYPE_ALLOWED",
        })

    def test_reference_acceptance_does_not_override_forbidden_action(self):
        candidate = {
            "text": "Reiniciar automaticamente o checkout.",
            "action_type": "change_environment",
            "cited_chunk_ids": ["RB-001-05"],
        }
        references = validate_candidate_references(candidate, [], [{"chunk_id": "RB-001-05"}])
        self.assertEqual(references, {
            "accepted": True,
            "validation_code": "REFERENCES_IN_CONTEXT",
            "invalid_chunk_ids": [],
        })
        self.assertFalse(validate_candidate_action(candidate)["allowed"])

    def test_allowed_action_does_not_override_invalid_references(self):
        candidate = {
            "action_type": "observe", "text": "Observar métricas.",
            "cited_chunk_ids": ["RB-999-01"],
        }
        self.assertTrue(validate_candidate_action(candidate)["allowed"])
        self.assertEqual(validate_candidate_references(candidate, [], []), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ["RB-999-01"],
        })

    def test_does_not_mutate_candidate(self):
        for value in ("observe", "request_verification", "change_environment", "unknown", [], {}, None):
            with self.subTest(value=value):
                candidate = {"text": "Texto manual", "action_type": value, "cited_chunk_ids": ["X"]}
                before = deepcopy(candidate)
                validate_candidate_action(candidate)
                self.assertEqual(candidate, before)


if __name__ == "__main__":
    unittest.main()
