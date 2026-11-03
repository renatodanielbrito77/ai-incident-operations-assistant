from copy import deepcopy
from html import escape
import unittest

from recommendation_models import RecommendationCandidate, CandidateStructureReport
from recommendation_structure import check_candidate_structure
from recommendation_report import render_candidate_report


class RecommendationReportTest(unittest.TestCase):
    def setUp(self):
        self.documentation = [{"chunk": {
            "chunk_id": "RB-001-04-02", "source": "docs/runbooks/example.md",
            "section": "Orientações", "subsection": "Verificações",
            "content": "Consultar monitoring e logs.\n\n  Preservar espaços e linhas.\n",
        }}]
        self.limits = [{
            "chunk_id": "RB-001-05", "source": "docs/runbooks/example.md",
            "section": "Limites", "content": "Não autoriza reinícios automáticos.",
        }]

    def models(self, ids=None, action="request_verification", text="Solicitar verificação dos logs."):
        candidate = RecommendationCandidate(
            text=text, action_type=action,
            cited_chunk_ids=["RB-001-04-02"] if ids is None else ids,
        )
        report = CandidateStructureReport.model_validate(check_candidate_structure(
            candidate.model_dump(), self.documentation, self.limits
        ))
        return candidate, report

    def render(self, **kwargs):
        return render_candidate_report(*self.models(**kwargs), self.documentation, self.limits)

    def assert_warnings(self, markdown):
        self.assertIn("Sustentação semântica não avaliada.", markdown)
        self.assertIn("Sustentação semântica: not_evaluated.", markdown)
        self.assertIn("não autoriza execução", markdown)
        self.assertIn("Não foi verificada contradição", markdown)

    def test_passed_candidate_is_presented_for_human_review(self):
        markdown = self.render()
        self.assertTrue(markdown.startswith("# Candidata para revisão humana"))
        self.assertIn("REFERENCES_IN_CONTEXT", markdown)
        self.assertIn("ACTION_TYPE_ALLOWED", markdown)
        self.assertIn("<pre>Solicitar verificação dos logs.</pre>", markdown)
        self.assertIn("<pre>request_verification</pre>", markdown)
        self.assert_warnings(markdown)

    def test_forbidden_candidate_highlights_rejection_and_reason(self):
        markdown = self.render(ids=["RB-001-05"], action="change_environment",
                               text="Reiniciar automaticamente o checkout.")
        self.assertTrue(markdown.startswith("# Candidata rejeitada"))
        self.assertIn("Não apresentar esta candidata como orientação a seguir.", markdown)
        self.assertIn("## Motivos da rejeição", markdown)
        self.assertIn("ACTION_TYPE_FORBIDDEN", markdown)
        self.assertIn("Não autoriza reinícios automáticos.", markdown)
        self.assert_warnings(markdown)

    def test_missing_reference_is_not_completed_from_other_sources(self):
        markdown = self.render(ids=["RB-001-04-02", "RB-999-01"])
        self.assertIn("REFERENCES_OUTSIDE_CONTEXT", markdown)
        self.assertIn("Não encontrada no contexto fornecido", markdown)
        self.assertIn("RB-999-01", markdown)
        self.assertIn(self.documentation[0]["chunk"]["content"], markdown)
        self.assertNotIn(self.limits[0]["content"], markdown)
        self.assert_warnings(markdown)

    def test_no_references_and_unknown_action_show_both_reasons(self):
        markdown = self.render(ids=[], action="unknown")
        self.assertIn("NO_REFERENCES", markdown)
        self.assertIn("UNKNOWN_ACTION_TYPE", markdown)
        self.assertIn("Nenhuma referência citada.", markdown)
        self.assertNotIn("### Referência", markdown)
        self.assert_warnings(markdown)

    def test_uncited_chunks_are_never_added(self):
        self.documentation.append({"chunk": {
            "chunk_id": "NOT-CITED", "content": "SEGREDO_NAO_CITADO",
            "source": "origem-nao-citada.md",
        }})
        markdown = self.render()
        for value in ("NOT-CITED", "SEGREDO_NAO_CITADO", "origem-nao-citada.md",
                      "RB-001-05", self.limits[0]["content"]):
            self.assertNotIn(value, markdown)

    def test_content_and_origin_preserve_whitespace_and_text(self):
        markdown = self.render()
        chunk = self.documentation[0]["chunk"]
        self.assertIn("<pre>" + escape(chunk["content"], quote=True) + "</pre>", markdown)
        self.assertIn("<pre>" + chunk["source"] + "</pre>", markdown)

    def test_titles_links_html_and_backticks_are_literal_in_all_user_fields(self):
        payload = '# Título\n[link](https://example.com)\n</pre><button>Executar</button>\n<script>alert(1)</script>\n`texto`\n```sh\ncomando\n```\nhttps://example.com'
        chunk = self.documentation[0]["chunk"]
        for field in ("content", "source", "section", "subsection"):
            chunk[field] = payload
        chunk["chunk_id"] = payload
        markdown = self.render(ids=[payload], action=payload, text=payload)
        literal = "<pre>" + escape(payload, quote=True) + "</pre>"
        self.assertEqual(markdown.count(literal), 7)
        self.assertNotIn("<button>", markdown)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("</pre><button>", markdown)
        # Todas as ocorrências das marcações da entrada estão dentro de pre.
        remaining = markdown.replace(literal, "")
        self.assertNotIn("# Título", remaining)
        self.assertNotIn("[link]", remaining)
        self.assertNotIn("```sh", remaining)
        self.assertNotIn("https://example.com", remaining)
        self.assert_warnings(markdown)

    def test_absent_origin_is_explicit_not_inferred(self):
        chunk = self.documentation[0]["chunk"]
        for field in ("source", "section", "subsection"):
            del chunk[field]
        markdown = self.render()
        self.assertIn("Origem: não fornecida no contexto.", markdown)
        self.assertNotIn("Seção:", markdown)
        self.assertNotIn("Subseção:", markdown)

    def test_missing_content_is_not_invented(self):
        del self.documentation[0]["chunk"]["content"]
        self.assertIn("Conteúdo não fornecido no contexto.", self.render())

    def test_duplicate_citations_render_once_in_declared_order(self):
        markdown = self.render(ids=["RB-001-05", "RB-001-04-02", "RB-001-05"])
        self.assertEqual(markdown.count("<pre>RB-001-05</pre>"), 1)
        self.assertLess(markdown.index("<pre>RB-001-05</pre>"), markdown.index("<pre>RB-001-04-02</pre>"))

    def test_contradictory_text_retains_semantic_limitation(self):
        markdown = self.render(ids=["RB-001-05"], action="observe",
                               text="Reiniciar automaticamente o checkout.")
        self.assertTrue(markdown.startswith("# Candidata para revisão humana"))
        self.assert_warnings(markdown)

    def test_does_not_mutate_inputs(self):
        for action in ("observe", "change_environment"):
            with self.subTest(action=action):
                candidate, report = self.models(action=action)
                before = deepcopy((candidate.model_dump(), report.model_dump(), self.documentation, self.limits))
                render_candidate_report(candidate, report, self.documentation, self.limits)
                self.assertEqual((candidate.model_dump(), report.model_dump(), self.documentation, self.limits), before)


if __name__ == "__main__":
    unittest.main()
