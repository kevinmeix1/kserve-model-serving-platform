from __future__ import annotations

import unittest

from kserve_model_platform.operator_console import IDENTITY, decorate_console


class OperatorConsoleTest(unittest.TestCase):
    def test_console_shell_is_offline_accessible_and_idempotent(self) -> None:
        source = (
            '<!doctype html><html><head><title>Run</title></head>'
            '<body class="report"><main>ok</main></body></html>'
        )

        rendered = decorate_console(source, active="dashboard")

        self.assertIn('class="operator-console report"', rendered)
        self.assertIn('id="main-content"', rendered)
        self.assertIn('aria-current="page"', rendered)
        self.assertIn('data-ui-system="operator-console-v2"', rendered)
        self.assertIn(IDENTITY.dashboard, rendered)
        self.assertNotIn("https://", rendered)
        self.assertEqual(decorate_console(rendered, active="dashboard"), rendered)

    def test_console_rejects_invalid_html(self) -> None:
        with self.assertRaisesRegex(ValueError, "body element"):
            decorate_console("<html><head></head></html>", active="dashboard")


if __name__ == "__main__":
    unittest.main()
