"""Lightweight pipeline tests.

Covers the integrity of the domain model (schema + attack catalogue) and a
fast mock-data -> report smoke test, so CI verifies the app actually runs in
addition to passing the security scans.
"""
import pathlib
import subprocess
import sys

import pandas as pd

from attacks import (
    ALL_TARGET_COLUMNS,
    ATTACKS,
    PUMP_OVERRIDE,
    SENSOR_SPOOFING,
    VALVE_MANIPULATION,
)
from schema import COLUMNS, EXPECTED_COLUMN_COUNT, TIMESTAMP_COL, column_kind

ROOT = pathlib.Path(__file__).resolve().parent.parent
VALID_CATEGORIES = {SENSOR_SPOOFING, VALVE_MANIPULATION, PUMP_OVERRIDE}


def test_schema_width_and_no_duplicates():
    assert len(COLUMNS) == EXPECTED_COLUMN_COUNT
    assert len(COLUMNS) == len(set(COLUMNS))
    assert COLUMNS[0] == TIMESTAMP_COL


def test_column_kind_classifies_by_suffix():
    assert column_kind("LIT101.Pv") == "pv"
    assert column_kind("MV101.Status") == "status"
    assert column_kind("P501.Speed") == "speed"
    assert column_kind("P1_STATE") == "state"
    assert column_kind("LS201.Alarm") == "alarm"
    assert column_kind(TIMESTAMP_COL) == "timestamp"


def test_attack_catalogue_integrity():
    assert len(ATTACKS) == 11
    for a in ATTACKS:
        assert a["category"] in VALID_CATEGORIES
        assert a["targets"], f"attack {a['id']} has no targets"
        for col in a["targets"]:
            assert col in COLUMNS, f"{col} is not a known schema column"


def test_all_target_columns_subset_of_schema():
    assert set(ALL_TARGET_COLUMNS).issubset(set(COLUMNS))


def test_mock_data_and_report_end_to_end(tmp_path):
    csv = tmp_path / "mock.csv"
    html = tmp_path / "report.html"

    subprocess.run(
        [sys.executable, "src/generate_mock_data.py",
         "--rows", "300", "--seed", "1", "--output", str(csv)],
        cwd=ROOT, check=True,
    )
    df = pd.read_csv(csv)
    assert df.shape == (300, EXPECTED_COLUMN_COUNT)

    subprocess.run(
        [sys.executable, "src/generate_report.py",
         "--input", str(csv), "--output", str(html)],
        cwd=ROOT, check=True,
    )
    assert "SWaT Attack Report" in html.read_text()
