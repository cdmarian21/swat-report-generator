"""List of attacks for the SWaT.A12 (Mar 2026) testbed

These attacks (and base data) were generously provided from:
Source: https://itrust.sutd.edu.sg/itrust-labs_datasets/
Dataset Version: SWaT.A12_Mar 2026
Authors: Goh, J., Adepu, S., Junejo, K. N., & Mathur, A.

This is used to identify the 11 labelled attacks during the second 4 hours
(13:00-end)

Design notes:
- Times format is "HH:MM:SS" 24-hour strings so they can be matched
  directly against the per-second Timestamp column in the CSV.
- `targets` lists the exact CSV column names of the primary sensor/actuator
  tags (sensors -> ".Pv", actuators -> ".Status"). Tag-range shorthand from
  the source table (e.g. "MV501-504", "P201-P206") is expanded into explicit
  columns so downstream code can index the dataframe directly.
- `category` is a single PRIMARY category per attack. A couple of attacks
  manipulate more than one device class; for those we pick the dominant
  mechanism and document the reasoning inline (see #2 and #3).
"""

# Canonical category labels. Defined as constants so a typo becomes an
# ImportError/NameError instead of a silently mis-bucketed attack.
SENSOR_SPOOFING = "Sensor Spoofing"
VALVE_MANIPULATION = "Valve Manipulation"
PUMP_OVERRIDE = "Pump Override"

ATTACKS = [
    {
        "id": 1,
        "name": "Stage 5 Valve Manipulation",
        "start": "13:00:00",
        "end": "13:05:00",
        "targets": ["MV501.Status", "MV502.Status", "MV503.Status", "MV504.Status"],
        "category": VALVE_MANIPULATION,
    },
    {
        "id": 2,
        "name": "Stage 1 Flow Disruption - MV101 Open, P101 & P102 Stop",
        "start": "13:40:00",
        "end": "13:45:00",
        "targets": ["MV101.Status", "P101.Status", "P102.Status"],
        # JUDGMENT CALL (mixed valve + pump). Categorised as PUMP_OVERRIDE:
        # the disruptive effect is achieved by stopping pumps P101/P102, with
        # MV101-open acting as the enabler. Defensible alternative:
        # VALVE_MANIPULATION (MV101 is the initiating action). Flip if you
        # prefer to lead with the valve.
        "category": PUMP_OVERRIDE,
    },
    {
        "id": 3,
        "name": "Florida Water Plant Scenario - Dosing Pump Activation & Sensor Spoofing",
        "start": "14:20:00",
        "end": "14:25:00",
        "targets": ["P201.Status", "P202.Status", "P203.Status", "P204.Status", "P205.Status", "P206.Status", "MV201.Status"],
        # JUDGMENT CALL (mixed pump + sensor spoofing). Categorised as
        # PUMP_OVERRIDE: the attack name leads with "Dosing Pump Activation"
        # and the dosing pumps P201-P206 are the primary manipulated devices.
        # Sensor spoofing is a secondary component.
        "category": PUMP_OVERRIDE,
    },
    {
        "id": 4,
        "name": "Tank Overflow via LIT101 Spoofing - Schneider Demo Attack 01",
        "start": "14:30:00",
        "end": "14:35:00",
        "targets": ["LIT101.Pv"],
        "category": SENSOR_SPOOFING,
    },
    {
        "id": 5,
        "name": "Stage 5 Valve Manipulation (Repeat)",
        "start": "14:40:00",
        "end": "14:45:00",
        "targets": ["MV501.Status", "MV502.Status", "MV503.Status", "MV504.Status"],
        "category": VALVE_MANIPULATION,
    },
    {
        "id": 6,
        "name": "Tank Overflow via LIT101 Spoofing",
        "start": "15:00:00",
        "end": "15:02:00",
        "targets": ["LIT101.Pv"],
        "category": SENSOR_SPOOFING,
    },
    {
        "id": 7,
        "name": "Stage 2 Parallel Pump Override - MV201, P101 & P102 Run",
        "start": "15:03:00",
        "end": "15:07:00",
        "targets": ["MV201.Status", "P101.Status", "P102.Status"],
        "category": PUMP_OVERRIDE,
    },
    {
        "id": 8,
        "name": "Reverse Osmosis Backwash Diversion - MV302 Close, MV303 Open",
        "start": "15:20:00",
        "end": "15:25:00",
        "targets": ["MV302.Status", "MV303.Status"],
        "category": VALVE_MANIPULATION,
    },
    {
        "id": 9,
        "name": "Forced Backwash Trigger via DPIT301 Spoofing - Ensign Pre-UAT Attack 1",
        "start": "15:45:00",
        "end": "15:50:00",
        "targets": ["DPIT301.Pv"],
        "category": SENSOR_SPOOFING,
    },
    {
        "id": 10,
        "name": "Multi-Value Level Oscillation - LIT601 Spoofing Sequence - Ensign Pre-UAT Attack 3",
        "start": "16:10:00",
        "end": "16:15:00",
        "targets": ["LIT601.Pv"],
        "category": SENSOR_SPOOFING,
    },
    {
        "id": 11,
        "name": "AIT402 High-Value Spoof Start - Using script",
        "start": "16:35:00",
        "end": "16:40:00",
        "targets": ["AIT402.Pv"],
        "category": SENSOR_SPOOFING,
    },
]

# Every distinct CSV column referenced by any attack. The mock-data generator
# uses this to guarantee it emits each attacked column; also handy for sanity
# checks against the real dataset header.
ALL_TARGET_COLUMNS = sorted({col for attack in ATTACKS for col in attack["targets"]})
