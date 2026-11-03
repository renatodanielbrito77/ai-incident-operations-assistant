from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
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

    def test_without_report_option_does_not_render_or_add_path(self):
        with patch.object(script, "render_candidate_report") as renderer:
            code, output = self.run_file(EXAMPLES / "request_verification.json")
        self.assertEqual(code, 0)
        self.assertNotIn("markdown_report_path", output)
        renderer.assert_not_called()

    def test_writes_same_generator_output_for_pass_and_rejection(self):
        for name, expected in (("request_verification.json", 0), ("change_environment.json", 1)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                documentation, limits = script.load_example_context(script.CHUNKS_PATH)
                with (
                    patch.object(script, "load_example_context", return_value=(documentation, limits)) as loader,
                    patch.object(script, "check_candidate_structure", wraps=script.check_candidate_structure) as checker,
                    patch.object(script, "render_candidate_report", wraps=script.render_candidate_report) as renderer,
                ):
                    code, output = self.run_file(EXAMPLES / name, report_path=path)
                self.assertEqual(code, expected)
                self.assertEqual(output["markdown_report_path"], str(path))
                loader.assert_called_once_with(script.CHUNKS_PATH)
                renderer.assert_called_once()
                candidate, report, rendered_docs, rendered_limits = renderer.call_args.args
                self.assertIs(checker.call_args.args[1], documentation)
                self.assertIs(checker.call_args.args[2], limits)
                self.assertIs(rendered_docs, documentation)
                self.assertIs(rendered_limits, limits)
                self.assertEqual(report.model_dump(), output["report"])
                self.assertEqual(path.read_text(encoding="utf-8"), script.render_candidate_report(
                    candidate, report, documentation, limits
                ))
                self.assertIn("Sustentação semântica não avaliada.", path.read_text(encoding="utf-8"))
                if expected == 1:
                    self.assertIn("Candidata rejeitada", path.read_text(encoding="utf-8"))
                    self.assertIn("ACTION_TYPE_FORBIDDEN", path.read_text(encoding="utf-8"))

    def test_invalid_candidate_never_opens_output_or_renders(self):
        for name, error in (("malformed.json", "JSON_INVALID"), ("invalid_contract.json", "CONTRACT_INVALID")):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                with patch.object(script, "render_candidate_report") as renderer:
                    code, output = self.run_file(EXAMPLES / name, report_path=path)
                self.assertEqual(code, 2)
                self.assertEqual(output["error"], error)
                self.assertFalse(path.exists())
                renderer.assert_not_called()
                path.write_text("Relatório anterior", encoding="utf-8")
                self.run_file(EXAMPLES / name, report_path=path)
                self.assertEqual(path.read_text(encoding="utf-8"), "Relatório anterior")

    def test_context_or_report_contract_error_creates_no_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            with patch.object(script, "load_example_context", side_effect=ValueError("Chunk ausente")):
                code, output = self.run_file(EXAMPLES / "request_verification.json", report_path=path)
            self.assertEqual(code, 2)
            self.assertEqual(output["error"], "CONTEXT_ERROR")
            self.assertFalse(path.exists())
            with patch.object(script, "check_candidate_structure", return_value={}):
                code, output = self.run_file(EXAMPLES / "request_verification.json", report_path=path)
            self.assertEqual(code, 2)
            self.assertEqual(output["error"], "REPORT_CONTRACT_ERROR")
            self.assertFalse(path.exists())

    def test_existing_destination_is_preserved(self):
        for name in ("request_verification.json", "change_environment.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                path.write_text("Conteúdo anterior", encoding="utf-8")
                code, output = self.run_file(EXAMPLES / name, report_path=path)
                self.assertEqual(code, 2)
                self.assertEqual(output["error"], "REPORT_WRITE_ERROR")
                self.assertEqual(path.read_text(encoding="utf-8"), "Conteúdo anterior")
                self.assertNotIn("markdown_report_path", output)

    def test_missing_directory_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing" / "report.md"
            code, output = self.run_file(EXAMPLES / "request_verification.json", report_path=path)
            self.assertEqual(code, 2)
            self.assertEqual(output["error"], "REPORT_WRITE_ERROR")
            self.assertFalse(path.parent.exists())

    def test_failure_during_write_is_operational_even_for_rejection(self):
        for name in ("request_verification.json", "change_environment.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                original_open = Path.open
                def failing_open(current_path, *args, **kwargs):
                    handle = original_open(current_path, *args, **kwargs)
                    if current_path == path and args and args[0] == "x":
                        from unittest.mock import MagicMock
                        wrapped = MagicMock()
                        wrapped.__enter__.return_value = wrapped
                        wrapped.write.side_effect = OSError("Disco cheio simulado")
                        wrapped.__exit__.side_effect = lambda *unused: handle.close()
                        return wrapped
                    return handle
                with patch.object(Path, "open", failing_open):
                    code, output = self.run_file(EXAMPLES / name, report_path=path)
                self.assertEqual(code, 2)
                self.assertEqual(output["error"], "REPORT_WRITE_ERROR")
                self.assertIn("Disco cheio simulado", output["details"])
                self.assertIn("gravação do Markdown não foi confirmada", output["message"])

    def test_cli_with_temporary_destinations(self):
        for name, expected in (("request_verification.json", 0), ("change_environment.json", 1)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                result = subprocess.run([
                    sys.executable, "-B", str(Path(script.__file__)),
                    "--candidate", str(EXAMPLES / name), "--report", str(path),
                ], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(output["markdown_report_path"], str(path))
                self.assertTrue(path.is_file())
                self.assertIn("not_evaluated", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
