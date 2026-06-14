"""Generate schema-faithful mock SWaT historian data for CI and demos.

The real SWaT CSV is sensitive, licensed, and too large to commit, so the
pipeline runs against synthetic data with the *same schema* (see schema.py).
Normal operation is emitted for the full run; each labelled attack then has its
target columns perturbed inside its window, so the report has a real
baseline-vs-attack signal to show.

Output is deterministic for a given --seed, so CI input is byte-identical on
every run: a failure is then a real failure, never RNG noise.

Run from the repo root:
    python src/generate_mock_data.py --output data/mock_swat.csv --seed 42
"""

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from attacks import ATTACKS
from schema import COLUMNS, EXPECTED_COLUMN_COUNT, TIMESTAMP_COL, column_kind

# The run starts at 09:00:00 on the dataset's capture date. One row per second.
RUN_START = datetime(2026, 3, 11, 9, 0, 0)
# The dataset documents 28,861 records over 09:00:00-17:00:59. (That span is
# arithmetically 28,860 seconds inclusive; the real file carries one extra
# record. We match the documented count so the mock's size mirrors reality.)
DEFAULT_ROWS = 28861

# Normal-operation baselines for each sensor (.Pv), seeded from the real
# dataset's opening rows so magnitudes are believable per sensor. Any .Pv not
# listed falls back to 1.0.
PV_BASELINES = {
    "LIT101.Pv": 809.67, "FIT101.Pv": 0.0,
    "FIT201.Pv": 0.0, "AIT201.Pv": 99.37, "AIT202.Pv": 9.99, "AIT203.Pv": 152.53,
    "AIT301.Pv": 7.71, "AIT302.Pv": 194.71, "AIT303.Pv": 31.02, "LIT301.Pv": 655.48,
    "FIT301.Pv": 0.0, "DPIT301.Pv": 3.62,
    "LIT401.Pv": 1006.40, "FIT401.Pv": 0.0, "AIT401.Pv": 0.0, "AIT402.Pv": 203.90,
    "FIT501.Pv": 0.0027, "FIT502.Pv": 0.0018, "FIT503.Pv": 0.0014, "FIT504.Pv": 0.0,
    "AIT501.Pv": 8.92, "AIT502.Pv": 305.15, "AIT503.Pv": 163.20, "AIT504.Pv": 29.84,
    "PIT501.Pv": 9.07, "PIT502.Pv": 0.0, "PIT503.Pv": 6.78,
    "LIT601.Pv": 341.64, "LIT602.Pv": 548.77, "FIT601.Pv": 0.0, "FIT602.Pv": 0.89,
}

# Normal alarm state per .Alarm column, from the dataset's opening rows. Any
# .Alarm not listed falls back to "Inactive".
ALARM_BASELINES = {
    "LS201.Alarm": "Inactive", "LS202.Alarm": "Inactive", "LSL203.Alarm": "Inactive",
    "LSLL203.Alarm": "Active",
    "PSH301.Alarm": "Bad Input", "DPSH301.Alarm": "Bad Input",
    "LS401.Alarm": "Inactive",
    "PSH501.Alarm": "Bad Input", "PSL501.Alarm": "Bad Input",
    "LSH601.Alarm": "Inactive", "LSL601.Alarm": "Inactive", "LSH602.Alarm": "Active",
    "LSL602.Alarm": "Inactive", "LSH603.Alarm": "Inactive", "LSL603.Alarm": "Active",
}

# Normal values for the discrete columns.
NORMAL_ACTUATOR_STATE = 1   # .Status / _STATE during normal operation
NORMAL_SPEED = 0            # .Speed during normal operation
# Value forced into an attacked actuator's column during its window. It only
# needs to differ clearly from NORMAL_ACTUATOR_STATE so the report shows a
# state change; the mock does not model open-vs-stop direction per attack.
ANOMALOUS_ACTUATOR_STATE = 2


def build_baseline(rng, n):
    """Build the normal-operation columns (everything except the timestamp)."""
    data = {}
    for col in COLUMNS:
        kind = column_kind(col)
        if kind == "pv":
            base = PV_BASELINES.get(col, 1.0)
            # Noise scaled to the sensor's magnitude; a small floor so flat-zero
            # sensors still jitter slightly. Clip at 0 (no negative readings).
            scale = max(abs(base) * 0.01, 0.001)
            data[col] = np.clip(np.round(rng.normal(base, scale, n), 6), 0, None)
        elif kind in ("status", "state"):
            data[col] = np.full(n, NORMAL_ACTUATOR_STATE, dtype=int)
        elif kind == "speed":
            data[col] = np.full(n, NORMAL_SPEED, dtype=int)
        elif kind == "alarm":
            data[col] = np.full(n, ALARM_BASELINES.get(col, "Inactive"), dtype=object)
    return data


def inject_attacks(df, ts_index, rng):
    """Perturb each attack's target columns inside its time window."""
    run_date = ts_index[0].date()
    for attack in ATTACKS:
        start_t = datetime.strptime(attack["start"], "%H:%M:%S").time()
        end_t = datetime.strptime(attack["end"], "%H:%M:%S").time()
        start_dt = datetime.combine(run_date, start_t)
        end_dt = datetime.combine(run_date, end_t)
        mask = (ts_index >= start_dt) & (ts_index <= end_dt)
        n = int(mask.sum())
        if n == 0:
            continue
        for col in attack["targets"]:
            kind = column_kind(col)
            if kind == "pv":
                # Spoof the reading well away from baseline so the window's
                # mean/min/max diverge visibly. Flat-zero sensors get a fixed
                # nonzero spike instead of a (meaningless) multiple of zero.
                base = PV_BASELINES.get(col, 1.0)
                spoof = 50.0 if base == 0 else base * 1.8
                scale = max(abs(spoof) * 0.02, 0.01)
                df.loc[mask, col] = np.clip(np.round(rng.normal(spoof, scale, n), 6), 0, None)
            elif kind in ("status", "state", "speed"):
                df.loc[mask, col] = ANOMALOUS_ACTUATOR_STATE


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/mock_swat.csv",
                        help="Path to write the mock CSV (default: data/mock_swat.csv)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for reproducible output (default: 42)")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS,
                        help=f"Number of one-per-second rows (default: {DEFAULT_ROWS})")
    return parser.parse_args()


def main():
    args = parse_args()

    if len(COLUMNS) != EXPECTED_COLUMN_COUNT:
        raise SystemExit(
            f"Schema integrity error: expected {EXPECTED_COLUMN_COUNT} columns, "
            f"found {len(COLUMNS)}."
        )

    rng = np.random.default_rng(args.seed)
    ts_index = pd.date_range(RUN_START, periods=args.rows, freq="s")

    df = pd.DataFrame(build_baseline(rng, args.rows))
    inject_attacks(df, ts_index, rng)

    # Match the real file's timestamp style (M/D/YYYY H:MM:SS, 24-hour).
    # %m/%d (zero-padded) keeps strftime cross-platform; %-m/%-d raises on
    # Windows. The report parses both padded and unpadded date forms.
    df.insert(0, TIMESTAMP_COL, ts_index.strftime("%m/%d/%Y %H:%M:%S"))
    df = df[COLUMNS]  # enforce canonical column order

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"Wrote {len(df):,} rows x {len(df.columns)} columns -> {output}")


if __name__ == "__main__":
    main()
