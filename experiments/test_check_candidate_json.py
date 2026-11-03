from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_candidate_json as script


EXAMPLES = Path(__file__).resolve().parent / "candidates"


class CheckCandidateJsonTest(unittest.TestCase):
    def run_file(self, path, **kwargs):
        output = io.StringIO()
        with redirect_stdout(output):
            code = script.run(path, **kwargs)
        return code, json.loads(output.getvalue())

    def run_data(self, data, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return self.run_file(path, **kwargs)

    def test_allowed_example_passes_structurally_without_semantic_evaluation(self):
        code, output = self.run_file(EXAMPLES / "request_verification.json")
        self.assertEqual(code, 0)
        self.assertEqual(output["report"], {
            "references": {"accepted": True, "validation_code": "REFERENCES_IN_CONTEXT", "invalid_chunk_ids": []},
            "action": {"allowed": True, "validation_code": "ACTION_TYPE_ALLOWED"},
            "structural_checks_passed": True,
            "semantic_support_status": "not_evaluated",
        })

    def test_forbidden_example_is_policy_rejection_not_format_error(self):
        code, output = self.run_file(EXAMPLES / "change_environment.json")
        self.assertEqual(code, 1)
        self.assertNotIn("error", output)
        self.assertTrue(output["report"]["references"]["accepted"])
        self.assertEqual(output["report"]["action"]["validation_code"], "ACTION_TYPE_FORBIDDEN")
        self.assertFalse(output["report"]["structural_checks_passed"])
        self.assertEqual(output["report"]["semantic_support_status"], "not_evaluated")

    def test_invalid_contract_skips_context_and_rules(self):
        with patch.object(script, "load_example_context") as context, patch.object(script, "check_candidate_structure") as check:
            code, output = self.run_file(EXAMPLES / "invalid_contract.json")
        self.assertEqual(code, 2)
        self.assertEqual(output["error"], "CONTRACT_INVALID")
        self.assertEqual(output["details"][0]["field"], "text")
        self.assertEqual(output["details"][0]["type"], "string_type")
        self.assertNotIn("report", output)
        context.assert_not_called()
        check.assert_not_called()

    def test_malformed_example_reports_line_column_and_skips_rules(self):
        with patch.object(script, "check_candidate_structure") as check:
            code, output = self.run_file(EXAMPLES / "malformed.json")
        self.assertEqual(code, 2)
        self.assertEqual(output["error"], "JSON_INVALID")
        self.assertGreater(output["details"]["line"], 0)
        self.assertGreater(output["details"]["column"], 0)
        self.assertNotIn("report", output)
        check.assert_not_called()

    def test_missing_candidate_file_is_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = self.run_file(Path(directory) / "missing.json")
        self.assertEqual(code, 2)
        self.assertEqual(output["error"], "INPUT_ERROR")

    def test_context_contains_only_exact_source_chunks_without_scores(self):
        documentation, limits = script.load_example_context(script.CHUNKS_PATH)
        source = json.loads(script.CHUNKS_PATH.read_text())
        self.assertEqual(documentation, [{"chunk": next(c for c in source if c["chunk_id"] == "RB-001-04-02")}])
        self.assertEqual(limits, [next(c for c in source if c["chunk_id"] == "RB-001-05")])
        code, output = self.run_file(EXAMPLES / "request_verification.json")
        self.assertEqual(code, 0)
        self.assertEqual(output["context"], {
            "documentation_chunk_ids": ["RB-001-04-02"],
            "document_limit_chunk_ids": ["RB-001-05"],
        })

    def test_either_missing_chunk_is_clear_context_error(self):
        source = json.loads(script.CHUNKS_PATH.read_text())
        for missing in ("RB-001-04-02", "RB-001-05"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "chunks.json"
                path.write_text(json.dumps([c for c in source if c["chunk_id"] != missing]))
                with patch.object(script, "check_candidate_structure") as check:
                    code, output = self.run_file(EXAMPLES / "request_verification.json", chunks_path=path)
                self.assertEqual(code, 2)
                self.assertEqual(output["error"], "CONTEXT_ERROR")
                self.assertIn(f"Chunk obrigatório ausente na origem: {missing}", output["details"])
                self.assertNotIn("report", output)
                check.assert_not_called()

    def test_duplicate_required_chunk_is_not_silently_selected(self):
        source = json.loads(script.CHUNKS_PATH.read_text())
        source.append(next(c for c in source if c["chunk_id"] == "RB-001-05"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chunks.json"
            path.write_text(json.dumps(source))
            code, output = self.run_file(EXAMPLES / "request_verification.json", chunks_path=path)
        self.assertEqual(code, 2)
        self.assertIn("duplicado", output["details"])

    def test_unreadable_or_invalid_context_is_context_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chunks.json"
            for content in (None, "{", "{}", "[1]"):
                with self.subTest(content=content):
                    if content is not None:
                        path.write_text(content)
                    code, output = self.run_file(EXAMPLES / "request_verification.json", chunks_path=path)
                    self.assertEqual(code, 2)
                    self.assertEqual(output["error"], "CONTEXT_ERROR")

    def test_reference_existing_in_source_but_not_context_is_rejected(self):
        code, output = self.run_data({
            "text": "Verificar dados.", "action_type": "observe",
            "cited_chunk_ids": ["RB-001-01"],
        })
        self.assertEqual(code, 1)
        self.assertEqual(output["report"]["references"]["invalid_chunk_ids"], ["RB-001-01"])
        self.assertEqual(output["report"]["semantic_support_status"], "not_evaluated")

    def test_contradictory_text_is_not_semantically_evaluated(self):
        code, output = self.run_data({
            "text": "Reiniciar automaticamente o checkout.",
            "action_type": "observe", "cited_chunk_ids": ["RB-001-05"],
        })
        self.assertEqual(code, 0)
        self.assertTrue(output["report"]["structural_checks_passed"])
        self.assertEqual(output["report"]["semantic_support_status"], "not_evaluated")

    def test_invalid_report_is_not_confused_with_candidate_contract(self):
        with patch.object(script, "check_candidate_structure", return_value={}):
            code, output = self.run_file(EXAMPLES / "request_verification.json")
        self.assertEqual(code, 2)
        self.assertEqual(output["error"], "REPORT_CONTRACT_ERROR")
        self.assertNotIn("report", output)

    def test_files_and_candidate_are_preserved(self):
        path = EXAMPLES / "request_verification.json"
        before = (path.read_bytes(), script.CHUNKS_PATH.read_bytes())
        data = json.loads(path.read_text())
        original = deepcopy(data)
        self.run_data(data)
        self.assertEqual(data, original)
        self.assertEqual((path.read_bytes(), script.CHUNKS_PATH.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
