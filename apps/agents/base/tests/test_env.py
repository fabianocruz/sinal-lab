"""Tests for apps.agents.base.env."""

import pytest

from apps.agents.base.env import int_from_env


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, 14),
        ("", 14),
        ("   ", 14),
        ("30", 30),
        (" 21 ", 21),
        ("abc", 14),
        ("7.5", 14),
        ("0", 14),
        ("-3", 14),
    ],
)
def test_int_from_env(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("X_DAYS", raising=False)
    else:
        monkeypatch.setenv("X_DAYS", raw)
    assert int_from_env("X_DAYS", 14) == expected


def test_minimum_is_configurable(monkeypatch):
    monkeypatch.setenv("X_DAYS", "3")
    assert int_from_env("X_DAYS", 14, minimum=5) == 14
    assert int_from_env("X_DAYS", 14, minimum=3) == 3
