from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import eval_candidates as evaluator


class EvalCandidatesTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(evaluator.CASES_PATH.read_text(encoding="utf-8"))
        self.chunks = json.loads(evaluator.CHUNKS_PATH.read_text(encoding="utf-8"))

    def run_inputs(self, data=None, chunks=None):
        with tempfile.TemporaryDirectory() as directory:
            cases_path = Path(directory) / "cases.json"
            chunks_path = Path(directory) / "chunks.json"
            cases_path.write_text(json.dumps(self.data if data is None else data), encoding="utf-8")
            chunks_path.write_text(json.dumps(self.chunks if chunks is None else chunks), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = evaluator.main(cases_path, chunks_path)
        return code, output.getvalue()

    def test_four_existing_cases_match_full_expectations(self):
        code, output = self.run_inputs()
        self.assertEqual(code, 0)
        self.assertIn("Expectativas estruturais atendidas: 4/4", output)
        self.assertIn("Expectativas estruturais não atendidas: 0", output)
        self.assertIn("Erros de execução: 0", output)
        self.assertEqual(output.count("Sustentação semântica automatizada: not_evaluated"), 4)

    def test_contradictory_case_is_not_presented_as_approval(self):
        code, output = self.run_inputs()
        self.assertEqual(code, 0)
        self.assertIn("CAND-003 — expectativa estrutural atendida; anotação humana: contradiz", output)
        self.assertIn("Expectativa atendida não significa aprovação da candidata.", output)
        self.assertNotIn("APROVADO", output)

    def test_context_only_uses_declared_chunks_and_preserves_case_four(self):
        with patch.object(evaluator, "check_candidate_structure", wraps=evaluator.check_candidate_structure) as check:
            code, _ = self.run_inputs()
        self.assertEqual(code, 0)
        self.assertEqual(check.call_count, 4)
        candidate, documentation, limits = check.call_args_list[3].args
        self.assertEqual(candidate["cited_chunk_ids"], ["RB-001-03-01"])
        self.assertEqual([item["chunk"]["chunk_id"] for item in documentation], ["RB-001-04-02"])
        self.assertEqual([item["chunk_id"] for item in limits], ["RB-001-05"])
        self.assertTrue(any(c["chunk_id"] == "RB-001-03-01" for c in self.chunks))

    def test_full_comparison_detects_invalid_id_order(self):
        case = self.data["cases"][3]
        case["candidate"]["cited_chunk_ids"] = ["RB-001-03-01", "RB-001-01"]
        case["expected_structure"]["references"]["invalid_chunk_ids"] = ["RB-001-01", "RB-001-03-01"]
        code, output = self.run_inputs()
        self.assertEqual(code, 1)
        self.assertIn("Campos divergentes: references", output)
        self.assertIn("Relatório esperado:", output)
        self.assertIn("Expectativas estruturais não atendidas: 1", output)
        self.assertIn("Erros de execução: 0", output)

    def test_valid_but_different_expected_action_is_expectation_failure(self):
        expected = self.data["cases"][0]["expected_structure"]
        expected["action"] = {"allowed": False, "validation_code": "ACTION_TYPE_FORBIDDEN"}
        expected["structural_checks_passed"] = False
        code, output = self.run_inputs()
        self.assertEqual(code, 1)
        self.assertIn("Campos divergentes: action, structural_checks_passed", output)

    def test_unknown_context_is_error_for_case_and_others_continue(self):
        self.data["cases"][0]["context_id"] = "MISSING"
        code, output = self.run_inputs()
        self.assertEqual(code, 2)
        self.assertIn("CAND-001 — ERRO DE EXECUÇÃO POR CASO", output)
        self.assertIn("Contexto referenciado inexistente: MISSING", output)
        self.assertNotIn("ERRO GLOBAL", output)
        self.assertIn("Expectativas estruturais atendidas: 3/4", output)

    def test_invalid_candidate_or_expectation_is_case_error(self):
        for field, value in (("candidate", {"text": 123}), ("expected_structure", {})):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                data["cases"][0][field] = value
                code, output = self.run_inputs(data)
                self.assertEqual(code, 2)
                self.assertIn("CAND-001 — ERRO DE EXECUÇÃO POR CASO", output)
                self.assertIn("Expectativas estruturais atendidas: 3/4", output)
                self.assertIn("Expectativas estruturais não atendidas: 0", output)

    def test_missing_case_payload_field_is_not_global(self):
        del self.data["cases"][0]["candidate"]
        code, output = self.run_inputs()
        self.assertEqual(code, 2)
        self.assertIn("CAND-001 — ERRO DE EXECUÇÃO POR CASO", output)

    def test_missing_chunk_is_case_context_error_not_empty_results(self):
        self.data["contexts"][0]["documentation_chunk_ids"] = ["MISSING"]
        with patch.object(evaluator, "check_candidate_structure") as check:
            code, output = self.run_inputs()
        self.assertEqual(code, 2)
        self.assertEqual(output.count("ERRO DE EXECUÇÃO POR CASO"), 4)
        self.assertNotIn("ERRO GLOBAL", output)
        self.assertIn("Erros de execução: 4", output)
        self.assertNotIn("Relatório observado:", output)
        check.assert_not_called()

    def test_malformed_json_is_global_and_skips_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text("{", encoding="utf-8")
            with patch.object(evaluator, "run_cases") as runner, redirect_stdout(io.StringIO()) as output:
                code = evaluator.main(path, evaluator.CHUNKS_PATH)
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL", output.getvalue())
        runner.assert_not_called()

    def test_duplicate_case_context_and_source_ids_are_global(self):
        for group in ("cases", "contexts", "chunks"):
            with self.subTest(group=group):
                data = deepcopy(self.data)
                chunks = deepcopy(self.chunks)
                records = chunks if group == "chunks" else data[group]
                records.append(deepcopy(records[0]))
                with patch.object(evaluator, "run_cases") as runner:
                    code, output = self.run_inputs(data, chunks)
                self.assertEqual(code, 2)
                self.assertIn("ERRO GLOBAL", output)
                self.assertIn("duplicado", output)
                runner.assert_not_called()

    def test_uninterpretable_manifest_and_missing_identifiers_are_global(self):
        for data in ([], {}, {"cases": [], "contexts": []}, {"cases": [{}], "contexts": []}):
            with self.subTest(data=data):
                code, output = self.run_inputs(data)
                self.assertEqual(code, 2)
                self.assertIn("ERRO GLOBAL", output)

    def test_missing_input_file_is_global(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            code = evaluator.main(Path(directory) / "missing.json", evaluator.CHUNKS_PATH)
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL", output.getvalue())

    def test_rule_exception_and_invalid_report_are_case_errors(self):
        for option in ({"side_effect": RuntimeError("Falha simulada")}, {"return_value": {}}):
            with self.subTest(option=option):
                with patch.object(evaluator, "check_candidate_structure", **option):
                    code, output = self.run_inputs()
                self.assertEqual(code, 2)
                self.assertIn("Erros de execução: 4", output)
                self.assertNotIn("Relatório observado:", output)
                self.assertNotIn("ERRO GLOBAL", output)

    def test_execution_error_takes_precedence_over_expectation_failure(self):
        self.data["cases"][0]["context_id"] = "MISSING"
        self.data["cases"][1]["expected_structure"]["action"] = {
            "allowed": False, "validation_code": "UNKNOWN_ACTION_TYPE"
        }
        code, output = self.run_inputs()
        self.assertEqual(code, 2)
        self.assertIn("Expectativas estruturais não atendidas: 1", output)
        self.assertIn("Erros de execução: 1", output)

    def test_human_annotation_does_not_change_structural_result(self):
        self.data["cases"][0]["human_semantic_annotation"] = {
            "assessment": "contradicts", "reason": "Anotação humana alternativa."
        }
        code, output = self.run_inputs()
        self.assertEqual(code, 0)
        self.assertIn("CAND-001 — expectativa estrutural atendida; anotação humana: contradiz", output)

    def test_invalid_human_annotation_is_case_error(self):
        self.data["cases"][0]["human_semantic_annotation"] = {"assessment": "unknown", "reason": "X"}
        code, output = self.run_inputs()
        self.assertEqual(code, 2)
        self.assertIn("CAND-001 — ERRO DE EXECUÇÃO POR CASO", output)
        self.assertIn("Expectativas estruturais atendidas: 3/4", output)

    def test_inputs_and_official_files_are_unchanged(self):
        files = (evaluator.CASES_PATH.read_bytes(), evaluator.CHUNKS_PATH.read_bytes())
        before = deepcopy((self.data, self.chunks))
        self.run_inputs()
        self.assertEqual((self.data, self.chunks), before)
        self.assertEqual((evaluator.CASES_PATH.read_bytes(), evaluator.CHUNKS_PATH.read_bytes()), files)


if __name__ == "__main__":
    unittest.main()
