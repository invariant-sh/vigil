"""Unit tests for MicroUsd."""

from __future__ import annotations

import pytest

from vigil.domain.money import MicroUsd


def test_from_usd_rounds_to_micro() -> None:
    money = MicroUsd.from_usd(0.75)
    assert money.micro_usd == 750_000
    assert money.display == "$0.750000"


def test_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        MicroUsd(micro_usd=-1)


def test_addition_and_comparison() -> None:
    a = MicroUsd(micro_usd=100)
    b = MicroUsd(micro_usd=50)
    assert (a + b).micro_usd == 150
    assert a > b
    assert b <= a
