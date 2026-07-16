#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


LOCAL_SCRIPT_PATH = Path(__file__).with_name("analyze_codex_turn.py")
SCRIPT_PATH = (
    LOCAL_SCRIPT_PATH
    if LOCAL_SCRIPT_PATH.exists()
    else Path(__file__).resolve().parents[1] / "scripts" / "analyze_codex_turn.py"
)
SPEC = importlib.util.spec_from_file_location("analyze_codex_turn", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)


class OutputStatsTest(unittest.TestCase):
    def test_reads_nested_unified_exec_result(self) -> None:
        output = [
            {"type": "input_text", "text": "Script completed\nWall time 3.0 seconds\nOutput:\n"},
            {
                "type": "input_text",
                "text": '{"wall_time_seconds":2.5,"exit_code":1,"original_token_count":42,"output":"lint failed"}',
            },
        ]

        stats = ANALYZER.output_stats(output, 2_000)

        self.assertEqual(stats["exit_code"], 1)
        self.assertEqual(stats["reported_wall_seconds"], 2.5)
        self.assertEqual(stats["original_token_count"], 42)
        self.assertEqual(stats["failure_kind"], "nonzero_exit")
        self.assertEqual(stats["completion_state"], "failed")

    def test_classifies_rejection_unsupported_and_yielded_cell(self) -> None:
        rejected = ANALYZER.output_stats(
            'Script failed\nScript error:\nRejected("This action was rejected due to unacceptable risk.")',
            2_000,
        )
        unsupported = ANALYZER.output_stats(
            "This method is not supported through raw CDP.",
            2_000,
        )
        yielded = ANALYZER.output_stats(
            "Script running with cell ID 7\nWall time 30.0 seconds\nOutput:\n",
            2_000,
        )
        lost_browser = ANALYZER.output_stats(
            "Script completed\nOutput:\nTab 1 is not part of browser session regression-session",
            2_000,
        )

        self.assertEqual(rejected["failure_kind"], "approval_rejected")
        self.assertEqual(unsupported["failure_kind"], "unsupported_tool_response")
        self.assertEqual(yielded["completion_state"], "yielded_cell")
        self.assertEqual(yielded["yielded_cell_id"], "7")
        self.assertEqual(lost_browser["failure_kind"], "browser_session_lost")


class EventAndClusterTest(unittest.TestCase):
    def test_counts_raw_compaction_instead_of_mirrored_notification(self) -> None:
        raw = {"type": "compacted", "payload": {}}
        mirrored = {"type": "event_msg", "payload": {"type": "context_compacted"}}

        self.assertTrue(ANALYZER.is_compaction_event(raw, True))
        self.assertFalse(ANALYZER.is_compaction_event(mirrored, True))
        self.assertTrue(ANALYZER.is_compaction_event(mirrored, False))

    def test_collapses_exec_poll_and_wait_calls_by_session(self) -> None:
        calls = [
            {
                "ordinal": 1,
                "name": "exec",
                "command": "tools.exec_command({})",
                "start_ts": "2026-07-15T00:00:00+00:00",
                "start_local": "2026-07-15 00:00:00 UTC",
                "end_ts": "2026-07-15T00:00:01+00:00",
                "output": {"session_id": 7, "completion_state": "running_session"},
            },
            {
                "ordinal": 2,
                "name": "exec",
                "command": "tools.write_stdin({session_id:7})",
                "start_ts": "2026-07-15T00:00:31+00:00",
                "start_local": "2026-07-15 00:00:31 UTC",
                "end_ts": "2026-07-15T00:00:32+00:00",
                "output": {"completion_state": "yielded_cell"},
                "arguments": None,
            },
            {
                "ordinal": 3,
                "name": "wait",
                "command": "",
                "start_ts": "2026-07-15T00:00:32+00:00",
                "start_local": "2026-07-15 00:00:32 UTC",
                "end_ts": "2026-07-15T00:00:33+00:00",
                "output": {"session_id": 7, "completion_state": "completed", "exit_code": 0},
                "arguments": {"cell_id": "8"},
            },
        ]
        calls[1]["output"]["yielded_cell_id"] = "8"

        ANALYZER.link_yielded_cells(calls)
        clusters = ANALYZER.build_process_clusters(calls)

        self.assertEqual(calls[1]["output"]["completion_state"], "yielded_then_completed")
        self.assertEqual(calls[1]["output"]["resolved_by_ordinal"], 3)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["root_ordinal"], 1)
        self.assertEqual(clusters[0]["poll_count"], 1)
        self.assertEqual(clusters[0]["wait_call_count"], 1)
        self.assertEqual(clusters[0]["call_ordinals"], [1, 2, 3])
        self.assertEqual(clusters[0]["completion_state"], "completed")


if __name__ == "__main__":
    unittest.main()
