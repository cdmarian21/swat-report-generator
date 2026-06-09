"""Canonical schema for the SWaT.A12 (Mar 2026) historian CSV.

Single source of truth for the dataset's structure. The mock-data generator
emits exactly these columns in this order, and the report reads against them,
so "works on mock in CI" reliably predicts "works on the real file locally".

Column naming convention (from the dataset):
    <TAG>.Pv      process value -> sensor reading        (float)
    <TAG>.Status  actuator state (valve / pump / UV)      (int)
    <TAG>.Speed   pump speed                              (int)
    P#_STATE      per-stage process state                 (int)
    <TAG>.Alarm   alarm state                             (str: Inactive/Active/Bad Input)
    t_stamp       per-second timestamp

`column_kind()` lets any consumer reason about a column's data type purely
from its name, so we never hard-code "which columns are floats" anywhere else.
"""

TIMESTAMP_COL = "t_stamp"

# Full 87-column header in dataset order: 1 timestamp + 86 tags spread across
# the six SWaT process stages (P1 raw water -> P6 permeate/backwash).
COLUMNS = [
    TIMESTAMP_COL,
    # --- P1: Raw water intake ---
    "P1_STATE", "LIT101.Pv", "FIT101.Pv", "MV101.Status", "P101.Status", "P102.Status",
    # --- P2: Chemical dosing ---
    "P2_STATE", "FIT201.Pv", "AIT201.Pv", "AIT202.Pv", "AIT203.Pv", "MV201.Status",
    "P201.Status", "P202.Status", "P203.Status", "P204.Status", "P205.Status",
    "P206.Status", "P207.Status", "P208.Status",
    "LS201.Alarm", "LS202.Alarm", "LSL203.Alarm", "LSLL203.Alarm",
    # --- P3: Ultrafiltration ---
    "P3_STATE", "AIT301.Pv", "AIT302.Pv", "AIT303.Pv", "LIT301.Pv", "FIT301.Pv",
    "DPIT301.Pv", "MV301.Status", "MV302.Status", "MV303.Status", "MV304.Status",
    "P301.Status", "P302.Status", "PSH301.Alarm", "DPSH301.Alarm",
    # --- P4: Dechlorination / UV ---
    "P4_STATE", "LIT401.Pv", "FIT401.Pv", "AIT401.Pv", "AIT402.Pv",
    "P401.Status", "P402.Status", "P403.Status", "P404.Status", "UV401.Status",
    "LS401.Alarm",
    # --- P5: Reverse osmosis ---
    "P5_STATE", "FIT501.Pv", "FIT502.Pv", "FIT503.Pv", "FIT504.Pv",
    "AIT501.Pv", "AIT502.Pv", "AIT503.Pv", "AIT504.Pv",
    "PIT501.Pv", "PIT502.Pv", "PIT503.Pv",
    "P501.Status", "P501.Speed", "P502.Status", "P502.Speed",
    "MV501.Status", "MV502.Status", "MV503.Status", "MV504.Status",
    "PSH501.Alarm", "PSL501.Alarm",
    # --- P6: Permeate / backwash ---
    "P6_STATE", "LIT601.Pv", "LIT602.Pv", "FIT601.Pv", "FIT602.Pv",
    "P601.Status", "P602.Status", "P603.Status",
    "LSH601.Alarm", "LSL601.Alarm", "LSH602.Alarm", "LSL602.Alarm",
    "LSH603.Alarm", "LSL603.Alarm",
]

# Expected width of the dataset. The generator checks against this so a typo in
# COLUMNS surfaces loudly instead of producing a silently malformed CSV.
EXPECTED_COLUMN_COUNT = 87

# Valid categorical values any .Alarm column may take.
ALARM_STATES = ("Inactive", "Active", "Bad Input")


def column_kind(col):
    """Classify a column by name suffix.

    Returns one of: 'timestamp', 'pv', 'status', 'speed', 'state', 'alarm'.
    Raises ValueError for an unrecognised name so schema drift can't pass silently.
    """
    if col == TIMESTAMP_COL:
        return "timestamp"
    if col.endswith(".Pv"):
        return "pv"
    if col.endswith(".Status"):
        return "status"
    if col.endswith(".Speed"):
        return "speed"
    if col.endswith(".Alarm"):
        return "alarm"
    if col.endswith("_STATE"):
        return "state"
    raise ValueError(f"Unrecognised column name: {col!r}")
