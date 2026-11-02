from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import eval_document_context as evaluator
import eval_retrieval


class EvalDocumentContextTest(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "TEST-001", "query": "Consulta fictícia",
            "expected_chunk_ids": ["RB-001-05"],
            "expected_behavior": "retrieve", "reason": "Recuperar limites",
        }
        self.abstain = {
            **self.case, "case_id": "TEST-002", "expected_behavior": "abstain",
            "expected_chunk_ids": [],
        }
        self.results = [{
            "chunk": {"chunk_id": "RB-001-04-02", "document_id": "RB-001"},
            "score": 0.71234567,
        }]
        # Não há score nos limites retornados por filtro.
        self.limits = [{"chunk_id": "RB-001-05", "document_id": "RB-001"}]
        self.search = Mock(return_value=self.results)
        self.get_limits = Mock(return_value=self.limits)

    def run_case(self, case=None, cases=None):
        output = io.StringIO()
        with redirect_stdout(output):
            code = evaluator.run_cases(
                cases if cases is not None else [case or self.case],
                self.search, self.get_limits,
            )
        return code, output.getvalue()

    def test_expected_id_only_in_limits_approves_with_separate_output(self):
        code, output = self.run_case()
        self.assertEqual(code, 0)
        self.assertIn("APROVADO", output)
        self.assertIn("Busca:\n  RB-001-04-02 — score=0.712346", output)
        self.assertIn("Limites acrescentados (por filtro, sem pontuação):\n  RB-001-05", output)
        self.assertNotIn("RB-001-05 — score=", output)
        self.assertIn('Contexto documental final: ["RB-001-04-02", "RB-001-05"]', output)
        self.search.assert_called_once_with("Consulta fictícia", top_k=3, min_similarity=0.50)
        self.get_limits.assert_called_once_with("RB-001")

    def test_expected_id_only_in_search_approves(self):
        self.get_limits.return_value = []
        code, _ = self.run_case({**self.case, "expected_chunk_ids": ["RB-001-04-02"]})
        self.assertEqual(code, 0)

    def test_expected_ids_distributed_between_sources_approve(self):
        code, _ = self.run_case({
            **self.case, "expected_chunk_ids": ["RB-001-04-02", "RB-001-05"]
        })
        self.assertEqual(code, 0)

    def test_missing_required_id_fails(self):
        code, output = self.run_case({**self.case, "expected_chunk_ids": ["RB-002-05"]})
        self.assertEqual(code, 1)
        self.assertIn("FALHOU", output)
        self.assertIn("Reprovados: 1", output)
        self.assertIn("Erros de execução: 0", output)

    def test_empty_search_skips_limits_and_approves_abstention(self):
        self.search.return_value = []
        code, output = self.run_case(self.abstain)
        self.assertEqual(code, 0)
        self.get_limits.assert_not_called()
        self.assertIn("Contexto documental final: []", output)

    def test_empty_search_does_not_invent_limits_for_retrieve(self):
        self.search.return_value = []
        code, _ = self.run_case()
        self.assertEqual(code, 1)
        self.get_limits.assert_not_called()

    def test_nonempty_context_fails_abstention(self):
        code, _ = self.run_case(self.abstain)
        self.assertEqual(code, 1)

    def test_unique_documents_and_final_ids_preserve_order(self):
        self.results.extend([
            {"chunk": {"chunk_id": "RB-001-05", "document_id": "RB-001"}, "score": 0.6},
            {"chunk": {"chunk_id": "RB-002-01", "document_id": "RB-002"}, "score": 0.55},
        ])
        self.get_limits.side_effect = [self.limits * 2, [
            {"chunk_id": "RB-002-05", "document_id": "RB-002"}
        ]]
        code, output = self.run_case()
        self.assertEqual(code, 0)
        self.assertEqual(self.get_limits.call_args_list, [call("RB-001"), call("RB-002")])
        self.assertIn(
            'Contexto documental final: ["RB-001-04-02", "RB-001-05", "RB-002-01", "RB-002-05"]',
            output,
        )

    def test_search_error_never_becomes_abstention(self):
        self.search.side_effect = OSError("Busca indisponível")
        code, output = self.run_case(self.abstain)
        self.assertEqual(code, 2)
        self.assertIn("ERRO DE EXECUÇÃO", output)
        self.assertIn("expectativa não avaliada", output)
        self.assertNotIn("Contexto documental final: []", output)
        self.get_limits.assert_not_called()

    def test_limits_error_does_not_approve_partial_context(self):
        self.get_limits.side_effect = OSError("Falha nos limites")
        code, output = self.run_case({**self.case, "expected_chunk_ids": ["RB-001-04-02"]})
        self.assertEqual(code, 2)
        self.assertIn("Aprovados: 0/1", output)
        self.assertIn("Reprovados: 0", output)
        self.assertIn("Erros de execução: 1", output)

    def test_error_in_later_document_rejects_partial_limits(self):
        self.results.append({
            "chunk": {"chunk_id": "RB-002-01", "document_id": "RB-002"}, "score": 0.6
        })
        self.get_limits.side_effect = [self.limits, RuntimeError("Falha de paginação")]
        code, output = self.run_case()
        self.assertEqual(code, 2)
        self.assertNotIn("APROVADO", output)

    def test_continues_after_error_and_error_exit_takes_precedence(self):
        self.search.side_effect = [self.results, OSError("Falha"), []]
        code, output = self.run_case(cases=[self.abstain, self.case, self.abstain])
        self.assertEqual(code, 2)
        self.assertIn("Aprovados: 1/3", output)
        self.assertIn("Reprovados: 1", output)
        self.assertIn("Erros de execução: 1", output)

    def test_does_not_mutate_cases_or_results(self):
        before = deepcopy((self.case, self.results, self.limits))
        self.run_case()
        self.assertEqual((self.case, self.results, self.limits), before)

    def test_cases_read_failure_is_global_and_skips_model(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(evaluator, "load_retrieval_functions") as loader:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = evaluator.main(Path(directory) / "missing.json")
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL", output.getvalue())
        self.assertNotIn("TEST-001", output.getvalue())
        loader.assert_not_called()

    def test_model_failure_is_global(self):
        with (
            patch.object(evaluator, "load_cases", return_value=[self.case]),
            patch.object(evaluator, "load_retrieval_functions", side_effect=RuntimeError("Modelo")),
            patch.object(evaluator, "run_cases") as runner,
        ):
            with redirect_stdout(io.StringIO()) as output:
                code = evaluator.main()
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL", output.getvalue())
        self.assertNotIn("TEST-001", output.getvalue())
        runner.assert_not_called()

    def test_main_reads_same_cases_with_simulated_functions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            text = json.dumps([self.case])
            path.write_text(text, encoding="utf-8")
            with patch.object(evaluator, "load_retrieval_functions", return_value=(self.search, self.get_limits)):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(evaluator.main(path), 0)
            self.assertEqual(path.read_text(), text)

    def test_shared_rule_keeps_search_and_context_evaluations_distinct(self):
        self.assertFalse(eval_retrieval.evaluate_case(self.case, self.results))
        code, _ = self.run_case()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
