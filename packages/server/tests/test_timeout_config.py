# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors
# SPDX-License-Identifier: MIT
"""Issue #20: the server suite runs under a per-test timeout, so a hang fails with a stack dump instead of stalling."""

import pytest


def test_every_server_test_runs_under_a_timeout(pytestconfig: pytest.Config) -> None:
    assert pytestconfig.pluginmanager.hasplugin("timeout")
    assert float(pytestconfig.getini("timeout")) > 0
    assert pytestconfig.getini("timeout_method") == "thread"
