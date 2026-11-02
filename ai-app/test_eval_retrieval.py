from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import eval_retrieval


class EvalRetrievalTest(unittest.TestCase):
    def setUp(self):
        self.retrieve = {
            "case_id": "RET-TEST-001",
            "query": "Consulta fictícia",
            "expected_chunk_ids": ["RB-001-04-02", "RB-001-03-02"],
            "expected_behavior": "retrieve",
            "reason": "Exigir os dois trechos",
        }
        self.abstain = {
            **self.retrieve,
            "case_id": "RET-TEST-002",
            "expected_chunk_ids": [],
            "expected_behavior": "abstain",
        }
        self.results = [
            {"chunk": {"chunk_id": chunk_id}, "score": score}
            for chunk_id, score in (
                ("RB-001-03-02", 0.71234567),
                ("RB-001-04-02", 0.61),
                ("RB-001-01", 0.55),
            )
        ]

    def run_cases(self, cases, search):
        output = io.StringIO()
        with redirect_stdout(output):
            code = eval_retrieval.run_cases(cases, search)
        return code, output.getvalue()

    def test_retrieve_approves_all_expected_ids_with_extra_results(self):
        search = Mock(return_value=self.results)
        code, output = self.run_cases([self.retrieve], search)
        self.assertEqual(code, 0)
        self.assertIn("APROVADO", output)
        self.assertIn("RET-TEST-001", output)
        self.assertIn('Esperados: ["RB-001-04-02", "RB-001-03-02"]', output)
        self.assertIn("RB-001-03-02 — score=0.712346", output)
        self.assertIn("RB-001-01 — score=0.550000", output)
        self.assertIn("Aprovados: 1/1", output)
        search.assert_called_once_with("Consulta fictícia", top_k=3, min_similarity=0.50)

    def test_retrieve_fails_if_one_required_id_is_missing(self):
        code, output = self.run_cases([self.retrieve], Mock(return_value=self.results[:1]))
        self.assertEqual(code, 1)
        self.assertIn("FALHOU", output)
        self.assertIn("Reprovados: 1", output)
        self.assertIn("Erros de execução: 0", output)

    def test_abstain_approves_only_empty_results(self):
        code, output = self.run_cases([self.abstain], Mock(return_value=[]))
        self.assertEqual(code, 0)
        self.assertIn("APROVADO", output)
        self.assertIn("Retornados: []", output)

    def test_abstain_fails_on_unwanted_result(self):
        code, output = self.run_cases([self.abstain], Mock(return_value=self.results[:1]))
        self.assertEqual(code, 1)
        self.assertIn("FALHOU", output)

    def test_operational_error_never_becomes_successful_abstention(self):
        search = Mock(side_effect=RuntimeError("Qdrant indisponível"))
        code, output = self.run_cases([self.abstain], search)
        self.assertEqual(code, 2)
        self.assertIn("ERRO DE EXECUÇÃO — RuntimeError: Qdrant indisponível", output)
        self.assertIn("expectativa não avaliada", output)
        self.assertNotIn("Retornados: []", output)
        self.assertNotIn("APROVADO", output)
        self.assertNotIn("FALHOU", output)
        self.assertIn("Aprovados: 0/1", output)
        self.assertIn("Reprovados: 0", output)
        self.assertIn("Erros de execução: 1", output)

    def test_execution_continues_and_error_exit_takes_precedence(self):
        search = Mock(side_effect=[[], OSError("Falha simulada"), []])
        code, output = self.run_cases([self.retrieve, self.abstain, {
            **self.abstain, "case_id": "RET-TEST-003"
        }], search)
        self.assertEqual(code, 2)
        self.assertIn("Aprovados: 1/3", output)
        self.assertIn("Reprovados: 1", output)
        self.assertIn("Erros de execução: 1", output)
        self.assertEqual(search.call_args_list, [
            call("Consulta fictícia", top_k=3, min_similarity=0.50)
        ] * 3)

    def test_malformed_results_are_execution_errors(self):
        for result in (None, [{"score": 0.7}], [{"chunk": {"chunk_id": "X"}}]):
            with self.subTest(result=result):
                code, output = self.run_cases([self.abstain], Mock(return_value=result))
                self.assertEqual(code, 2)
                self.assertIn("ERRO DE EXECUÇÃO", output)
                self.assertNotIn("Retornados: []", output)

    def assert_global_error(self, path):
        with patch.object(eval_retrieval, "load_search") as loader:
            output = io.StringIO()
            with redirect_stdout(output):
                code = eval_retrieval.main(path)
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL", output.getvalue())
        self.assertNotIn("\nRET-TEST-001\n", output.getvalue())
        self.assertNotIn("ERRO DE EXECUÇÃO", output.getvalue())
        loader.assert_not_called()

    def test_missing_cases_file_is_global_error(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_global_error(Path(directory) / "missing.json")

    def test_invalid_json_is_global_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text("{", encoding="utf-8")
            self.assert_global_error(path)

    def test_invalid_case_contract_is_global_error(self):
        invalid_cases = [[], {}, [self.retrieve, self.retrieve]]
        for change in (
            {"expected_behavior": "unknown"},
            {"expected_chunk_ids": []},
            {"query": " "},
            {"expected_chunk_ids": ["X", "X"]},
            {"expected_chunk_ids": [None]},
        ):
            invalid_cases.append([{**self.retrieve, **change}])
        invalid_cases.append([{**self.abstain, "expected_chunk_ids": ["X"]}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            for cases in invalid_cases:
                with self.subTest(cases=cases):
                    path.write_text(json.dumps(cases), encoding="utf-8")
                    self.assert_global_error(path)

    def test_model_loading_error_is_global_not_assigned_to_case(self):
        search = Mock()
        with (
            patch.object(eval_retrieval, "load_cases", return_value=[self.retrieve]),
            patch.object(eval_retrieval, "load_search", side_effect=RuntimeError("Modelo indisponível")),
            patch.object(eval_retrieval, "run_cases", search),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                code = eval_retrieval.main()
        self.assertEqual(code, 2)
        self.assertIn("ERRO GLOBAL — RuntimeError: Modelo indisponível", output.getvalue())
        self.assertNotIn("RET-TEST-001", output.getvalue())
        search.assert_not_called()

    def test_main_reads_cases_and_uses_loaded_search_without_mutation(self):
        cases = [self.retrieve, self.abstain]
        before = deepcopy((cases, self.results))
        search = Mock(side_effect=[self.results, []])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            with patch.object(eval_retrieval, "load_search", return_value=search):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(eval_retrieval.main(path), 0)
            self.assertEqual(json.loads(path.read_text()), cases)
        self.assertEqual((cases, self.results), before)


if __name__ == "__main__":
    unittest.main()
