import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

pyqt5_module = types.ModuleType("PyQt5")
qtcore_module = types.ModuleType("PyQt5.QtCore")


class _QObject:
    pass


def _pyqtSignal(*_args, **_kwargs):
    return None


qtcore_module.QObject = _QObject
qtcore_module.pyqtSignal = _pyqtSignal
pyqt5_module.QtCore = qtcore_module

sys.modules.setdefault("PyQt5", pyqt5_module)
sys.modules.setdefault("PyQt5.QtCore", qtcore_module)
sys.modules.setdefault("instrument_app.widgets.CustomWidgets", types.ModuleType("instrument_app.widgets.CustomWidgets"))

from instrument_app.widgets.Channels import UserInput


class UserInputResponseFilteringTests(unittest.TestCase):
    def test_filters_only_exact_command_match(self):
        values, responses = UserInput._filter_user_input_responses(
            "TP_1:POWR?",
            ["TP_1:POWR?5", "TP_1:POWR_LONG?7"],
        )

        self.assertEqual(values, ["5"])
        self.assertEqual(responses, ["TP_1:POWR?5"])

    def test_query_command_accepts_equals_response(self):
        values, responses = UserInput._filter_user_input_responses(
            "TP_1:POWR?",
            ["TP_1:POWR=5", "OTHER=2"],
        )

        self.assertEqual(values, ["5"])
        self.assertEqual(responses, ["TP_1:POWR=5"])

    def test_checksum_suffix_is_ignored_for_matching(self):
        values, responses = UserInput._filter_user_input_responses(
            "TP_1:POWR?",
            ["TP_1:POWR?5@ABCD"],
        )

        self.assertEqual(values, ["5"])
        self.assertEqual(responses, ["TP_1:POWR?5"])

    def test_multi_command_preserves_submitted_command_order(self):
        values, responses = UserInput._filter_user_input_responses(
            "A?;B=1",
            ["B=2", "A?1", "A?3"],
        )

        self.assertEqual(values, ["1", "3", "2"])
        self.assertEqual(responses, ["A?1", "A?3", "B=2"])


if __name__ == "__main__":
    unittest.main()
