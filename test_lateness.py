"""Four tests: exclusions, redaction, a 3-day slice, and a regression on this week's verdicts. Run: pytest -q"""
from collections import Counter

import lateness as L
from lateness import Params, evaluate


def test_exclusions():
    rows, valid, excluded, converted = L.load()
    assert (len(rows), len(valid)) == (5292, 5249)
    assert Counter(r for _, r in excluded) == {"UNPARSEABLE": 24, "ARRIVAL_BEFORE_DEPARTURE": 18, "DUPLICATE": 1}
    assert ("T1-03237", "DUPLICATE") in excluded          # twin of T1-03235, runtime 40 vs 45
    assert converted == [("T1-02864", "TZ_CORRECTED")]    # +00:00 converted, kept, not dropped as early
    t = next(t for t in L.measure(valid, Params())[0] if t["trip_id"] == "T1-02864")
    assert t["lateness_min"] == -2
    # extreme trips are never trimmed: all 19 of R-35's Wednesday stay in
    wed = [t for t in valid if t["route"] == "R-35" and t["scheduled_departure"].startswith("2026-08-05")]
    assert len(wed) == 19
    # caller exclusions carry a reason and change the counts
    r = evaluate(Params(exclude={i: "SECOND_TIME_SOURCE" for i in (t["trip_id"] for t in wed)}))
    assert r["scope"]["trips"] == 5249 - 19 and r["refund_queue"]["trips"] == 10


def test_redaction():
    """HANDOFF (a): a fake phone column, and phone/email planted in fields, never reach any tool output."""
    import csv, json, server
    fixture = L.ROOT / "_redaction_fixture.csv"
    cols = ["trip_id", "route", "vehicle_series", "scheduled_departure", "scheduled_runtime_min",
            "actual_arrival", "tz_offset", "rider_phone", "complaint_text"]
    rows = [["T1-00001", "R-01", "01", f"2026-08-0{d} 06:00", "50", f"2026-08-0{d} 07:00", "+05:30",
             "+91 90000 12345", "never came, mail me at rider@example.com"] for d in (3, 4, 5)]
    rows[0][0] = "T1-00002"
    rows[1][0], rows[1][5] = "rider@example.com", "2026-08-04 07:30"   # email-shaped id on a refund-queue trip
    rows[2][0], rows[2][5] = "9000012345", "2026-08-05 08:60"          # phone-shaped id on an excluded trip
    try:
        with open(fixture, "w", newline="") as f:
            csv.writer(f).writerows([cols] + rows)
        out = json.dumps([server.route_verdicts(Params(trips_file=fixture.name)), server.data_quality(fixture.name)])
        for leak in ("90000", "9000012345", "rider@example.com", "never came", "rider_phone", "complaint_text"):
            assert leak not in out, leak
    finally:
        fixture.unlink(missing_ok=True)
    assert L.redact({"a": "call +91 90000 12345, x@y.in", "ids": ["T1-00001", "2026-08-03 17:11"]}) == \
        {"a": "call , ", "ids": ["T1-00001", "2026-08-03 17:11"]}
    full = evaluate()
    assert L.redact(full) == full                                 # no false hits on real ids and timestamps
    assert all(set(x) == {"line", "categories"} for x in server.ops_log()["lines"])


def test_three_day_slice():
    r = evaluate(Params(days=["2026-08-03", "2026-08-04", "2026-08-05"]))
    assert r["scope"]["days"] == ["2026-08-03", "2026-08-04", "2026-08-05"]
    v = {x["route"]: x for x in r["routes"]}
    assert all(x["days"] == 3 for x in v.values())
    # route_share 0.5 over 3 days: LATE needs 2 late days
    assert (v["R-14"]["verdict"], v["R-14"]["late_days"]) == ("LATE", 3)
    assert (v["R-35"]["verdict"], v["R-35"]["late_days"]) == ("NOT LATE", 1)   # Wednesday alone can't carry it
    assert (v["R-26"]["late_days"], v["R-26"]["flip_trips"]) == (1, 1)         # Mon 7/14: one trip from a 2nd day
    assert not any(x["low_confidence"] for x in v.values())                   # 3 days, every day >= 5 trips
    two = evaluate(Params(days=["2026-08-03", "2026-08-04"]))["routes"]      # thin slice: verdict kept, tagged
    assert {x["verdict"] for x in two} <= {"LATE", "NOT LATE"} and all(x["low_confidence"] for x in two)


def test_regression_this_week():
    r = evaluate()
    assert r["late_routes"] == ["R-14"]
    assert [(w["route"], w["verdict"], w["pct_late"], w["p85"], w["late_days"], w["flip_trips"]) for w in r["worst_three"]] == [
        ("R-14", "LATE", 72.0, 12.0, 7, 11), ("R-33", "NOT LATE", 47.1, 9.55, 2, 3), ("R-26", "NOT LATE", 42.7, 8.0, 3, 1)]
    assert sum(x["verdict"] == "NOT LATE" for x in r["routes"]) == 39
    assert r["refund_queue"]["trips"] == 29 and r["refund_queue"]["by_route"] == {"R-08": 1, "R-09": 1, "R-14": 8, "R-35": 19}
    assert [(i["route"], i["day"], i["trips"], i["mean"]) for i in r["incidents"]] == [("R-35", "2026-08-05", 19, 51.3)]
    side = {s["route"]: s for s in L.rec114_side_column()}
    assert side["R-14"]["rec114_from_effective"]["late_trips"] == 51 and side["R-14"]["rec114_whole_week"]["late_trips"] == 37
    assert evaluate(Params(rec114="by_vehicle_class"))["rec114"]["trips_remeasured"] == 0
