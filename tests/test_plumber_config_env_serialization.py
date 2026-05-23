"""Tests for ``.env`` serialization helpers in :mod:`src.agent.plumber_config`."""

from __future__ import annotations

import pytest
from src.agent.plumber_config import (
    format_dotenv_value,
    serialize_plumber_config_field_for_dotenv,
)


def test_format_dotenv_value_quotes_dollar_sign() -> None:
    assert format_dotenv_value("plain") == "plain"
    quoted = format_dotenv_value("a$b")
    assert quoted.startswith('"')
    assert quoted.endswith('"')
    assert "$" in quoted


def test_serialize_thermal_rejects_nan_and_inf() -> None:
    with pytest.raises(ValueError, match="finite"):
        serialize_plumber_config_field_for_dotenv("thermal_delay_bootstrap", float("nan"))
    with pytest.raises(ValueError, match="finite"):
        serialize_plumber_config_field_for_dotenv("thermal_delay_cognitive", float("inf"))
    assert serialize_plumber_config_field_for_dotenv("thermal_delay_bootstrap", 1.5) == "1.5"


def test_serialize_thermal_accepts_int() -> None:
    assert serialize_plumber_config_field_for_dotenv("thermal_delay_bootstrap", 2) == "2.0"
