"""Route lateness for Priya's Friday review. Stdlib + pydantic, deterministic; the model never computes a number.

Cleaning (remove only rows that cannot be true, each with a reason code; never trim for being extreme):
  UNPARSEABLE               arrival/departure/runtime does not parse (e.g. arrival "08:60")
  ARRIVAL_BEFORE_DEPARTURE  arrival, converted to +05:30, is earlier than scheduled departure
  DUPLICATE                 same route, scheduled departure and arrival as an earlier row (runtime may
                            differ: T1-03235/T1-03237 are 45 vs 40); the lowest trip_id is kept
  <caller's reason>         trips excluded through Params.exclude, e.g. a second time source
  TZ_CORRECTED (kept)       arrival stamped with another offset is converted to +05:30

Defaults are the signed-off rules (see DECISION.md); every one is a Params field for the debrief.
"""
import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Literal

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "assignment" / "data"
IST = timezone(timedelta(hours=5, minutes=30))
FMT = "%Y-%m-%d %H:%M"


class Params(BaseModel):
    late_min: float = Field(5, description="A trip is late when it arrives more than this many minutes after departure + runtime.")
    late_inclusive: bool = Field(False, description="True: exactly late_min counts as late. Default False (5:00 is within whole-minute clock error).")
    early_min: float | None = Field(None, description="None: early counts as on time. A number: trips more than this many minutes early also count against the route.")
    day_share: float = Field(0.5, description="A route-day is late when MORE than this share of its valid trips are late.")
    route_share: float = Field(0.5, description="A route is LATE when MORE than this share of the days in scope are late (4 of 7 at 0.5).")
    min_days: int = Field(3, description="Tag low_confidence when a route has fewer days of data than this.")
    min_day_trips: int = Field(5, description="Tag low_confidence when any day in scope has fewer valid trips than this.")
    days: list[str] | None = Field(None, description="Only these departure dates (YYYY-MM-DD). None = all.")
    hours: tuple[int, int] | None = Field(None, description="Only departures with hour in [from, to), e.g. [6, 11] for the AM peak. None = all.")
    exclude: dict[str, str] = Field(default_factory=dict, description="Extra trips to exclude: {trip_id: REASON_CODE}.")
    rec114: Literal["off", "by_route", "by_vehicle_class"] = Field("off", description="REC-114 revised runtimes: off (default), by_route (routes in schedule_v2), by_vehicle_class (4xx series only).")
    rec114_from_effective: bool = Field(True, description="Apply REC-114 only to trips on/after schedule_v2's effective_date; False = whole week.")
    rank_by: Literal["share_late", "p85", "median", "mean"] = Field("share_late", description="Worst-three metric. Tie-break: p85, then route id.")
    incident_median_min: float = Field(15, description="A route-day is an incident when its median lateness exceeds this.")
    refund_min: float = Field(15, description="Trips more than this many minutes late go to the refund queue (CESL cap).")
    trips_file: str = Field("assignment/data/trips.csv", description="CSV to read, relative to the repo; must stay inside it.")


# ---------- cleaning ----------

def _offset(s):
    sign = -1 if s.startswith("-") else 1
    h, m = s.lstrip("+-").split(":")
    return timezone(sign * timedelta(hours=int(h), minutes=int(m)))


def clean(rows):
    """-> (valid, excluded [(trip_id, reason)], converted [(trip_id, reason)])."""
    valid, excluded, converted, seen = [], [], [], set()
    for r in sorted(rows, key=lambda r: r["trip_id"]):
        try:
            dep = datetime.strptime(r["scheduled_departure"], FMT).replace(tzinfo=IST)
            arr = datetime.strptime(r["actual_arrival"], FMT).replace(tzinfo=_offset(r["tz_offset"]))
            runtime = int(r["scheduled_runtime_min"])
        except (ValueError, KeyError, AttributeError):
            excluded.append((r.get("trip_id"), "UNPARSEABLE"))
            continue
        if r["tz_offset"] != "+05:30":
            converted.append((r["trip_id"], "TZ_CORRECTED"))
        if arr < dep:
            excluded.append((r["trip_id"], "ARRIVAL_BEFORE_DEPARTURE"))
            continue
        key = (r["route"], r["scheduled_departure"], arr)
        if key in seen:
            excluded.append((r["trip_id"], "DUPLICATE"))
            continue
        seen.add(key)
        # whitelist: only these fields ever leave the module (retention memo, HANDOFF (a))
        valid.append(dict(trip_id=r["trip_id"], route=r["route"], vehicle_series=r["vehicle_series"],
                          scheduled_departure=r["scheduled_departure"], scheduled_runtime_min=runtime,
                          actual_arrival=arr.astimezone(IST).strftime(FMT),
                          actual_runtime_min=(arr - dep).total_seconds() / 60))
    return valid, excluded, converted


def resolve(path):
    p = (ROOT / path).resolve()
    if ROOT not in p.parents or p.suffix != ".csv":
        raise ValueError(f"{path}: only .csv files inside the repo are readable")
    return p


@lru_cache(maxsize=8)
def _load(path, mtime):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, *clean(rows)


def load(trips_file="assignment/data/trips.csv"):
    p = resolve(trips_file)
    return _load(str(p), p.stat().st_mtime)


def schedule_v2():
    with open(DATA / "schedule_v2.csv", newline="") as f:
        return {s["route"]: s for s in csv.DictReader(f)}


# ---------- measuring ----------

def measure(valid, p: Params):
    """Applies filters, extra exclusions and REC-114; adds lateness_min and late (bool)."""
    sched = schedule_v2()
    out, rec114_hits = [], 0
    for r in valid:
        day, hour = r["scheduled_departure"][:10], int(r["scheduled_departure"][11:13])
        if r["trip_id"] in p.exclude or (p.days and day not in p.days) or (p.hours and not p.hours[0] <= hour < p.hours[1]):
            continue
        runtime = r["scheduled_runtime_min"]
        s = sched.get(r["route"])
        selected = s and (p.rec114 == "by_route" or (p.rec114 == "by_vehicle_class" and re.fullmatch(r"4\d\d", r["vehicle_series"])))
        if selected and (not p.rec114_from_effective or day >= s["effective_date"]):
            runtime, rec114_hits = int(s["revised_runtime_min"]), rec114_hits + 1
        lat = r["actual_runtime_min"] - runtime
        late = lat >= p.late_min if p.late_inclusive else lat > p.late_min
        early = p.early_min is not None and lat < -p.early_min
        out.append({**r, "runtime_used_min": runtime, "lateness_min": lat, "late": late or early})
    return out, rec114_hits


def p85(xs):
    """85th percentile, linear interpolation between closest ranks (inclusive method)."""
    return quantiles(xs, n=20, method="inclusive")[16] if len(xs) > 1 else xs[0]


def route_table(trips, p: Params):
    scope = sorted({t["scheduled_departure"][:10] for t in trips})
    by = defaultdict(lambda: defaultdict(list))
    for t in trips:
        by[t["route"]][t["scheduled_departure"][:10]].append(t)
    K = math.floor(p.route_share * len(scope))       # LATE needs late_days > K
    rows = []
    for route, days in by.items():
        cells = {d: (len(days.get(d, [])), sum(t["late"] for t in days.get(d, []))) for d in scope}
        thr = {d: math.floor(p.day_share * n) for d, (n, _) in cells.items()}   # late day needs late > thr
        is_late = {d: n > 0 and l > thr[d] for d, (n, l) in cells.items()}
        k = sum(is_late.values())
        lat = [t["lateness_min"] for d in days for t in days[d]]
        # every route gets LATE or NOT LATE; thin data is tagged, not withheld
        low_conf = sum(n > 0 for n, _ in cells.values()) < p.min_days or any(n < p.min_day_trips for n, _ in cells.values())
        if k > K:
            verdict = "LATE"
            flip = sum(sorted(l - thr[d] for d, (n, l) in cells.items() if is_late[d])[: k - K])
        else:
            verdict = "NOT LATE"
            costs = sorted(thr[d] + 1 - l for d, (n, l) in cells.items() if n and not is_late[d])
            flip = sum(costs[: K + 1 - k]) if len(costs) >= K + 1 - k else None
        n = len(lat)
        late = sum(c[1] for c in cells.values())
        rows.append(dict(route=route, verdict=verdict, low_confidence=low_conf, flip_trips=flip, trips=n, late_trips=late,
                         pct_late=round(100 * late / n, 1), share_late=late / n, median=median(lat),
                         p85=round(p85(lat), 2), mean=round(mean(lat), 2), late_days=k, days=len(scope),
                         per_day={d: dict(trips=c[0], late=c[1], late_day=is_late[d],
                                           median=median(t["lateness_min"] for t in days[d]) if c[0] else None)
                                  for d, c in cells.items()}))
    rows.sort(key=lambda r: (-r[p.rank_by], -r["p85"], r["route"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows, scope


def incidents(trips, threshold):
    days = defaultdict(list)
    for t in trips:
        days[(t["route"], t["scheduled_departure"][:10])].append(t)
    out = []
    for (route, day), ts in sorted(days.items()):
        lat = [t["lateness_min"] for t in ts]
        if median(lat) > threshold:
            out.append(dict(route=route, day=day, trips=len(ts), median=median(lat), mean=round(mean(lat), 1),
                            min=min(lat), max=max(lat),
                            departures=f'{min(t["scheduled_departure"][11:] for t in ts)}-{max(t["scheduled_departure"][11:] for t in ts)}',
                            trip_ids=sorted(t["trip_id"] for t in ts),
                            action="flag as incident; trips to refund review; device team to check"))
    return out


def evaluate(p: Params | None = None):
    p = p or Params()
    rows, valid, excluded, converted = load(p.trips_file)
    trips, hits = measure(valid, p)
    table, scope = route_table(trips, p)
    refund = sorted((t for t in trips if t["lateness_min"] > p.refund_min), key=lambda t: t["trip_id"])
    return dict(
        params=p.model_dump(),
        scope=dict(days=scope, trips=len(trips), rows_in_file=len(rows), valid=len(valid),
                   excluded=dict(Counter(r for _, r in excluded)) | ({"CALLER": len(p.exclude)} if p.exclude else {}),
                   converted=[t for t, _ in converted]),
        late_routes=[r["route"] for r in table if r["verdict"] == "LATE"],
        network=dict(routes=len(table), median_route_pct_late=round(100 * median(r["share_late"] for r in table), 1),
                     routes_under_80pct_on_time=sum(r["share_late"] > 0.20 for r in table),
                     routes_under_75pct_on_time=sum(r["share_late"] > 0.25 for r in table)),
        worst_three=[{k: r[k] for k in ("rank", "route", "verdict", "pct_late", "p85", "late_days", "flip_trips")} for r in table[:3]],
        routes=table,
        incidents=incidents(trips, p.incident_median_min),
        refund_queue=dict(trips=len(refund), by_route=dict(Counter(t["route"] for t in refund)),
                          trip_ids=[t["trip_id"] for t in refund]),
        rec114=dict(mode=p.rec114, trips_remeasured=hits),
    )


def rec114_side_column(p: Params | None = None):
    """Labelled side column only: schedule_v2 routes re-measured under REC-114, next to the verdict basis."""
    p = p or Params()
    base = {r["route"]: r for r in evaluate(p.model_copy(update={"rec114": "off"}))["routes"]}
    out = []
    for route, s in schedule_v2().items():
        row = dict(route=route, revised_runtime_min=int(s["revised_runtime_min"]), effective_date=s["effective_date"],
                   note=s["note"], as_published={k: base[route][k] for k in ("verdict", "late_trips", "trips", "late_days")})
        for label, from_eff in (("rec114_from_effective", True), ("rec114_whole_week", False)):
            r = next(x for x in evaluate(p.model_copy(update={"rec114": "by_route", "rec114_from_effective": from_eff}))["routes"]
                     if x["route"] == route)
            row[label] = {k: r[k] for k in ("verdict", "late_trips", "trips", "late_days")}
        out.append(row)
    return out


# ---------- redaction (HANDOFF (a): no rider phone numbers or verbatim complaint text) ----------

PII = re.compile(r"(?:\+?91[\s-]?)?(?<!\d)[6-9]\d{4}[\s-]?\d{5}(?!\d)|\d{10,}"   # phone-shaped
                 r"|[\w.+-]+@[\w-]+\.[\w.-]+")                                          # email-shaped


def redact(obj):
    """Applied to every tool output. Unknown columns never reach outputs (clean() whitelists fields);
    anything phone- or email-shaped in any string is blanked as a second line of defence."""
    if isinstance(obj, str):
        return PII.sub("", obj)
    if isinstance(obj, dict):
        return {redact(k): redact(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    return obj


# ---------- ops log: referenced by line number and category only, never by text ----------

OPS_CATEGORIES = [("weather/diversion", r"waterlog|flood|rain|divert"), ("crowding", r"crowd|surge|festival"),
                  ("staffing", r"driver|no-show"), ("vehicle", r"swap|breakdown"), ("complaint", r"complaint"),
                  ("normal", r"\bnormal\b|good day")]


def ops_log():
    """Categories per line by fixed keyword rules; the line text is never returned."""
    out = []
    with open(DATA / "ops_log.txt") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                cats = [c for c, rx in OPS_CATEGORIES if re.search(rx, line, re.I)] or ["uncategorised"]
                out.append(dict(line=i, categories=cats))
    return out
