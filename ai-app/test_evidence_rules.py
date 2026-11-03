from copy import deepcopy
import unittest

from evidence_rules import has_log_message


class EvidenceRulesTest(unittest.TestCase):
    def entry(self, message, level="INFO"):
        return {
            "timestamp": "2026-10-05T12:00:00Z",
            "level": level,
            "message": message,
        }

    def test_empty_list_returns_false(self):
        self.assertIs(has_log_message([]), False)

    def test_blank_messages_return_false(self):
        entries = [self.entry(message) for message in ("", " ", "\t", "\n\r", " \t\n ")]
        self.assertIs(has_log_message(entries), False)

    def test_nonempty_message_returns_true(self):
        self.assertIs(has_log_message([self.entry("Timeout observado")]), True)

    def test_edge_whitespace_does_not_hide_text(self):
        self.assertIs(has_log_message([self.entry(" \t registro \n")]), True)

    def test_one_nonblank_message_is_sufficient_in_any_position(self):
        for messages in (("registro", "", " "), ("", "registro", " "), ("", " ", "registro")):
            with self.subTest(messages=messages):
                self.assertIs(has_log_message([
                    self.entry(message) for message in messages
                ]), True)

    def test_level_does_not_change_result(self):
        for level in ("DEBUG", "INFO", "WARN", "ERROR", "", "CUSTOM"):
            with self.subTest(level=level):
                self.assertIs(has_log_message([self.entry("registro", level)]), True)
                self.assertIs(has_log_message([self.entry(" ", level)]), False)

    def test_message_content_is_not_interpreted(self):
        for message in ("x", "0", ".", "Tudo normal", "estranho", "Password reset email delivery failed"):
            with self.subTest(message=message):
                self.assertIs(has_log_message([self.entry(message)]), True)

    def test_does_not_mutate_inputs(self):
        for messages in (("", " \t"), (" \t registro \n", "")):
            with self.subTest(messages=messages):
                entries = [self.entry(message) for message in messages]
                before = deepcopy(entries)
                has_log_message(entries)
                self.assertEqual(entries, before)


if __name__ == "__main__":
    unittest.main()
