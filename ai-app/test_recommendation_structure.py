from copy import deepcopy
import unittest
from unittest.mock import patch

from recommendation_rules import validate_candidate_action, validate_candidate_references
from recommendation_structure import check_candidate_structure


class RecommendationStructureTest(unittest.TestCase):
    def setUp(self):
        self.documentation = [{
            "chunk": {"chunk_id": "RB-001-04-02", "content": "Consultar monitoring e logs."}
        }]
        self.limits = [{
            "chunk_id": "RB-001-05", "content": "Não autoriza reinícios automáticos."
        }]

    def candidate(self, ids, action_type):
        return {
            "text": "Texto fornecido manualmente.",
            "cited_chunk_ids": ids,
            "action_type": action_type,
        }

    def assert_checks(self, candidate, references_accepted, action_allowed, passed):
        result = check_candidate_structure(candidate, self.documentation, self.limits)
        self.assertEqual(set(result), {
            "references", "action", "structural_checks_passed", "semantic_support_status"
        })
        self.assertEqual(result["references"], validate_candidate_references(
            candidate, self.documentation, self.limits
        ))
        self.assertEqual(result["action"], validate_candidate_action(candidate))
        self.assertIs(result["references"]["accepted"], references_accepted)
        self.assertIs(result["action"]["allowed"], action_allowed)
        self.assertIs(result["structural_checks_passed"], passed)
        self.assertEqual(result["semantic_support_status"], "not_evaluated")
        return result

    def test_accepted_references_and_allowed_action_pass(self):
        self.assert_checks(self.candidate(["RB-001-04-02"], "observe"), True, True, True)

    def test_accepted_references_and_forbidden_action_fail(self):
        self.assert_checks(self.candidate(["RB-001-05"], "change_environment"), True, False, False)

    def test_rejected_references_and_allowed_action_fail(self):
        self.assert_checks(self.candidate(["RB-999-01"], "request_verification"), False, True, False)

    def test_rejected_references_and_forbidden_action_fail(self):
        self.assert_checks(self.candidate(["RB-999-01"], "change_environment"), False, False, False)

    def test_contradictory_text_passes_only_structural_checks(self):
        candidate = {
            "text": "Reiniciar automaticamente o checkout para resolver o incidente.",
            "action_type": "observe",
            "cited_chunk_ids": ["RB-001-05"],
        }
        result = self.assert_checks(candidate, True, True, True)
        self.assertEqual(result["references"]["validation_code"], "REFERENCES_IN_CONTEXT")
        self.assertEqual(result["action"]["validation_code"], "ACTION_TYPE_ALLOWED")

    def test_no_references_preserves_code_and_empty_invalid_ids(self):
        result = self.assert_checks(self.candidate([], "observe"), False, True, False)
        self.assertEqual(result["references"], {
            "accepted": False, "validation_code": "NO_REFERENCES", "invalid_chunk_ids": []
        })

    def test_unknown_action_preserves_code(self):
        for action in ("unknown", None, [], {}):
            with self.subTest(action=action):
                result = self.assert_checks(self.candidate(["RB-001-05"], action), True, False, False)
                self.assertEqual(result["action"]["validation_code"], "UNKNOWN_ACTION_TYPE")

    def test_calls_both_existing_validators_once_even_when_references_fail(self):
        candidate = self.candidate(["RB-999-01"], "observe")
        with (
            patch("recommendation_structure.validate_candidate_references",
                  wraps=validate_candidate_references) as references,
            patch("recommendation_structure.validate_candidate_action",
                  wraps=validate_candidate_action) as action,
        ):
            result = check_candidate_structure(candidate, self.documentation, self.limits)
        references.assert_called_once_with(candidate, self.documentation, self.limits)
        action.assert_called_once_with(candidate)
        self.assertEqual(result["references"]["invalid_chunk_ids"], ["RB-999-01"])
        self.assertTrue(result["action"]["allowed"])
        self.assertFalse(result["structural_checks_passed"])

    def test_does_not_modify_inputs_for_any_combination(self):
        for ids in (["RB-001-05"], ["RB-999-01"], []):
            for action in ("observe", "change_environment", None):
                with self.subTest(ids=ids, action=action):
                    candidate = self.candidate(ids, action)
                    before = deepcopy((candidate, self.documentation, self.limits))
                    check_candidate_structure(candidate, self.documentation, self.limits)
                    self.assertEqual((candidate, self.documentation, self.limits), before)


if __name__ == "__main__":
    unittest.main()
