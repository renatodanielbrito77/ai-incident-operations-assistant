from copy import deepcopy
import unittest

from recommendation_rules import validate_candidate_references


class RecommendationRulesTest(unittest.TestCase):
    def setUp(self):
        self.documentation = [{
            "score": 0.8,
            "chunk": {
                "chunk_id": "RB-001-04-02",
                "content": "Consultar monitoring e logs de pagamentos.",
            },
        }]
        self.limits = [{
            "chunk_id": "RB-001-05",
            "content": "Não autoriza reinícios automáticos.",
        }]

    def validate(self, ids, text="Consultar monitoring e logs de pagamentos."):
        return validate_candidate_references(
            {"text": text, "cited_chunk_ids": ids}, self.documentation, self.limits
        )

    def assert_accepted_references(self, result):
        self.assertEqual(result, {
            "accepted": True,
            "validation_code": "REFERENCES_IN_CONTEXT",
            "invalid_chunk_ids": [],
        })

    def test_reference_in_documentation(self):
        self.assert_accepted_references(self.validate(["RB-001-04-02"]))

    def test_reference_in_limits(self):
        self.assert_accepted_references(self.validate(["RB-001-05"]))

    def test_references_in_both_sources(self):
        self.assert_accepted_references(self.validate(["RB-001-04-02", "RB-001-05"]))

    def test_reference_outside_context(self):
        self.assertEqual(self.validate(["RB-999-01"]), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ["RB-999-01"],
        })

    def test_mixed_valid_and_invalid_references_are_rejected(self):
        self.assertEqual(self.validate(["RB-001-05", "RB-999-01", "RB-001-04-02"]), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ["RB-999-01"],
        })

    def test_no_references_includes_empty_invalid_list(self):
        self.assertEqual(self.validate([]), {
            "accepted": False,
            "validation_code": "NO_REFERENCES",
            "invalid_chunk_ids": [],
        })

    def test_empty_context_rejects_references(self):
        self.documentation = []
        self.limits = []
        self.assertEqual(self.validate(["RB-001-04-02"]), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ["RB-001-04-02"],
        })

    def test_empty_context_and_no_references(self):
        self.documentation = []
        self.limits = []
        self.test_no_references_includes_empty_invalid_list()

    def test_duplicate_valid_references_do_not_change_acceptance(self):
        self.assert_accepted_references(self.validate([
            "RB-001-05", "RB-001-05", "RB-001-04-02"
        ]))

    def test_invalid_ids_are_unique_and_preserve_first_occurrence_order(self):
        self.assertEqual(self.validate([
            "RB-999-02", "RB-001-05", "RB-999-01", "RB-999-02", "RB-999-01"
        ]), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ["RB-999-02", "RB-999-01"],
        })

    def test_ids_are_compared_exactly_without_normalization(self):
        ids = ["rb-001-05", " RB-001-05", "RB-001-05 "]
        self.assertEqual(self.validate(ids), {
            "accepted": False,
            "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
            "invalid_chunk_ids": ids,
        })

    def test_duplicate_context_ids_do_not_change_acceptance(self):
        self.documentation *= 2
        self.limits += [{"chunk_id": "RB-001-04-02"}]
        self.assert_accepted_references(self.validate(["RB-001-04-02"]))

    def test_reference_acceptance_does_not_approve_recommendation_text(self):
        self.assert_accepted_references(self.validate(
            ["RB-001-05"], text="Reiniciar automaticamente a aplicação."
        ))
        self.assert_accepted_references(self.validate(["RB-001-05"], text=""))

    def test_does_not_modify_inputs_for_any_result(self):
        for ids in ([], ["RB-001-05"], ["RB-999-02", "RB-999-02", "RB-001-05"]):
            with self.subTest(ids=ids):
                candidate = {"text": "Texto manual", "cited_chunk_ids": ids}
                before = deepcopy((candidate, self.documentation, self.limits))
                validate_candidate_references(candidate, self.documentation, self.limits)
                self.assertEqual((candidate, self.documentation, self.limits), before)


if __name__ == "__main__":
    unittest.main()
