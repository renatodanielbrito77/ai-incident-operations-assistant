from copy import deepcopy
import unittest

from pydantic import ValidationError

from recommendation_models import (
    RecommendationCandidate, ReferenceValidationResult,
    ActionValidationResult, CandidateStructureReport,
)
from recommendation_structure import check_candidate_structure


class RecommendationModelsTest(unittest.TestCase):
    def setUp(self):
        self.candidate = {
            "text": "Solicitar verificação dos logs de pagamentos.",
            "action_type": "request_verification",
            "cited_chunk_ids": ["RB-001-04-02"],
        }
        self.documentation = [{"chunk": {"chunk_id": "RB-001-04-02"}}]
        self.limits = [{"chunk_id": "RB-001-05"}]
        self.report = {
            "references": {
                "accepted": True, "validation_code": "REFERENCES_IN_CONTEXT",
                "invalid_chunk_ids": [],
            },
            "action": {"allowed": True, "validation_code": "ACTION_TYPE_ALLOWED"},
            "structural_checks_passed": True,
            "semantic_support_status": "not_evaluated",
        }

    def check(self, data):
        candidate = RecommendationCandidate.model_validate(data)
        result = check_candidate_structure(
            candidate.model_dump(), self.documentation, self.limits
        )
        return CandidateStructureReport.model_validate(result)

    def test_well_formed_candidate_and_report_pass_without_semantic_evaluation(self):
        result = self.check(self.candidate)
        self.assertTrue(result.structural_checks_passed)
        self.assertEqual(result.semantic_support_status, "not_evaluated")
        self.assertEqual(result.model_dump(), self.report)

    def test_wrong_action_type_is_format_error(self):
        with self.assertRaises(ValidationError) as raised:
            self.check({**self.candidate, "action_type": 123})
        error = raised.exception.errors()[0]
        self.assertEqual(error["loc"], ("action_type",))
        self.assertEqual(error["type"], "string_type")

    def test_well_formed_forbidden_action_is_policy_rejection(self):
        result = self.check({
            **self.candidate, "text": "Reiniciar automaticamente o checkout.",
            "action_type": "change_environment", "cited_chunk_ids": ["RB-001-05"],
        })
        self.assertTrue(result.references.accepted)
        self.assertFalse(result.action.allowed)
        self.assertEqual(result.action.validation_code, "ACTION_TYPE_FORBIDDEN")
        self.assertFalse(result.structural_checks_passed)
        self.assertEqual(result.semantic_support_status, "not_evaluated")

    def test_unknown_and_blank_action_strings_reach_policy(self):
        for action in ("restart", "", " ", "OBSERVE", " observe "):
            with self.subTest(action=action):
                result = self.check({**self.candidate, "action_type": action})
                self.assertEqual(result.action.validation_code, "UNKNOWN_ACTION_TYPE")
                self.assertFalse(result.structural_checks_passed)

    def test_empty_reference_list_reaches_no_references_rule(self):
        result = self.check({**self.candidate, "cited_chunk_ids": []})
        self.assertEqual(result.references.validation_code, "NO_REFERENCES")
        self.assertEqual(result.references.invalid_chunk_ids, [])
        self.assertFalse(result.structural_checks_passed)

    def test_blank_text_and_ids_are_format_errors(self):
        for value in ("", " ", "\t\n"):
            for field, content in (("text", value), ("cited_chunk_ids", [value])):
                with self.subTest(field=field, content=content):
                    with self.assertRaises(ValidationError):
                        RecommendationCandidate.model_validate({**self.candidate, field: content})

    def test_string_fields_and_items_do_not_coerce_other_types(self):
        for value in ([], {}, 0, 1.5, True, False, None):
            for field, content in (
                ("text", value), ("action_type", value), ("cited_chunk_ids", [value])
            ):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError):
                        RecommendationCandidate.model_validate({**self.candidate, field: content})

    def test_reference_container_must_be_list(self):
        for value in (("RB-001-05",), "RB-001-05", {}, True, None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    RecommendationCandidate.model_validate({**self.candidate, "cited_chunk_ids": value})

    def test_candidate_fields_are_required_and_extras_forbidden(self):
        for field in self.candidate:
            with self.subTest(missing=field):
                data = {k: v for k, v in self.candidate.items() if k != field}
                with self.assertRaises(ValidationError):
                    RecommendationCandidate.model_validate(data)
        with self.assertRaises(ValidationError):
            RecommendationCandidate.model_validate({**self.candidate, "extra": "X"})

    def test_spaces_and_inputs_are_preserved(self):
        data = {"text": "  Texto manual \n", "action_type": " observe ",
                "cited_chunk_ids": [" RB-001-05 "]}
        before = deepcopy(data)
        model = RecommendationCandidate.model_validate(data)
        self.assertEqual(model.model_dump(), before)
        self.assertEqual(data, before)
        result = self.check(data)
        self.assertEqual(result.references.invalid_chunk_ids, [" RB-001-05 "])

    def test_all_existing_result_codes_can_be_represented(self):
        for accepted, code, ids in (
            (True, "REFERENCES_IN_CONTEXT", []),
            (False, "REFERENCES_OUTSIDE_CONTEXT", ["MISSING"]),
            (False, "NO_REFERENCES", []),
        ):
            with self.subTest(code=code):
                ReferenceValidationResult(accepted=accepted, validation_code=code, invalid_chunk_ids=ids)
        for allowed, code in (
            (True, "ACTION_TYPE_ALLOWED"), (False, "ACTION_TYPE_FORBIDDEN"),
            (False, "UNKNOWN_ACTION_TYPE"),
        ):
            with self.subTest(code=code):
                ActionValidationResult(allowed=allowed, validation_code=code)

    def test_result_models_require_all_fields_and_forbid_extras(self):
        for model, payload in (
            (ReferenceValidationResult, self.report["references"]),
            (ActionValidationResult, self.report["action"]),
            (CandidateStructureReport, self.report),
        ):
            for field in payload:
                with self.subTest(model=model.__name__, missing=field):
                    with self.assertRaises(ValidationError):
                        model.model_validate({k: v for k, v in payload.items() if k != field})
            with self.subTest(model=model.__name__, extra=True):
                with self.assertRaises(ValidationError):
                    model.model_validate({**payload, "extra": True})

    def test_strict_booleans_in_report_and_nested_models(self):
        for value in (0, 1, "true", "false", None):
            for field in ("accepted", "allowed", "structural_checks_passed"):
                with self.subTest(field=field, value=value):
                    data = deepcopy(self.report)
                    if field == "accepted":
                        data["references"][field] = value
                    elif field == "allowed":
                        data["action"][field] = value
                    else:
                        data[field] = value
                    with self.assertRaises(ValidationError):
                        CandidateStructureReport.model_validate(data)

    def test_unknown_codes_and_semantic_status_are_rejected(self):
        for target in ("references", "action", "semantic_support_status"):
            with self.subTest(target=target):
                data = deepcopy(self.report)
                if target == "semantic_support_status":
                    data[target] = "evaluated"
                else:
                    data[target]["validation_code"] = "UNKNOWN_CODE"
                with self.assertRaises(ValidationError):
                    CandidateStructureReport.model_validate(data)

    def test_inconsistent_reference_results_are_rejected(self):
        for accepted, code, ids in (
            (False, "REFERENCES_IN_CONTEXT", []),
            (True, "NO_REFERENCES", []),
            (True, "REFERENCES_OUTSIDE_CONTEXT", ["X"]),
            (False, "REFERENCES_OUTSIDE_CONTEXT", []),
            (False, "NO_REFERENCES", ["X"]),
            (True, "REFERENCES_IN_CONTEXT", ["X"]),
        ):
            with self.subTest(accepted=accepted, code=code, ids=ids):
                with self.assertRaises(ValidationError):
                    ReferenceValidationResult(accepted=accepted, validation_code=code, invalid_chunk_ids=ids)

    def test_invalid_id_list_is_strict_and_nonblank(self):
        for value in (("X",), "X", [None], [1], [True], [" "], None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    ReferenceValidationResult.model_validate({
                        "accepted": False, "validation_code": "REFERENCES_OUTSIDE_CONTEXT",
                        "invalid_chunk_ids": value,
                    })

    def test_inconsistent_action_results_are_rejected(self):
        for allowed, code in (
            (False, "ACTION_TYPE_ALLOWED"), (True, "ACTION_TYPE_FORBIDDEN"),
            (True, "UNKNOWN_ACTION_TYPE"),
        ):
            with self.subTest(allowed=allowed, code=code):
                with self.assertRaises(ValidationError):
                    ActionValidationResult(allowed=allowed, validation_code=code)

    def test_structural_flag_matches_both_checks_for_all_combinations(self):
        for accepted in (False, True):
            for allowed in (False, True):
                with self.subTest(accepted=accepted, allowed=allowed):
                    data = deepcopy(self.report)
                    if not accepted:
                        data["references"].update(accepted=False, validation_code="NO_REFERENCES")
                    if not allowed:
                        data["action"].update(allowed=False, validation_code="ACTION_TYPE_FORBIDDEN")
                    data["structural_checks_passed"] = accepted and allowed
                    CandidateStructureReport.model_validate(data)
                    data["structural_checks_passed"] = not data["structural_checks_passed"]
                    with self.assertRaises(ValidationError):
                        CandidateStructureReport.model_validate(data)

    def test_contradictory_text_can_pass_structurally_without_semantic_support(self):
        result = self.check({
            "text": "Reiniciar automaticamente o checkout.",
            "action_type": "observe", "cited_chunk_ids": ["RB-001-05"],
        })
        self.assertTrue(result.structural_checks_passed)
        self.assertEqual(result.semantic_support_status, "not_evaluated")


if __name__ == "__main__":
    unittest.main()
