"""Read-only MCP server over this week's Cityflo trips. Run: python3 server.py (stdio)."""
from mcp.server.fastmcp import FastMCP

import lateness as L
from lateness import Params, redact

mcp = FastMCP("cityflo-lateness")


@mcp.tool()
def route_verdicts(params: Params | None = None) -> dict:
    """One verdict per route (LATE / NOT LATE, tagged low_confidence on thin data) with flip_trips (trips whose status must
    change to reverse it), the ranked worst three, incident days, the refund queue and data scope.
    Defaults are the signed-off rules; every rule is adjustable through params."""
    return redact(L.evaluate(params))


@mcp.tool()
def what_if(params: Params) -> dict:
    """Re-run with changed rules and compare to the signed-off defaults: verdicts that flip, worst three
    before/after, LATE routes and refund-queue size before/after."""
    base, alt = L.evaluate(), L.evaluate(params)
    b = {r["route"]: r for r in base["routes"]}
    flips = [dict(route=r["route"], before=b[r["route"]]["verdict"], after=r["verdict"],
                  late_days=f'{b[r["route"]]["late_days"]}/{b[r["route"]]["days"]} -> {r["late_days"]}/{r["days"]}')
             for r in alt["routes"] if r["route"] in b and r["verdict"] != b[r["route"]]["verdict"]]
    return redact(dict(params=alt["params"], verdict_changes=flips,
                       late_routes=dict(before=base["late_routes"], after=alt["late_routes"]),
                       worst_three=dict(before=base["worst_three"], after=alt["worst_three"]),
                       refund_queue_trips=dict(before=base["refund_queue"]["trips"], after=alt["refund_queue"]["trips"]),
                       scope=alt["scope"]))


@mcp.tool()
def route_detail(route: str, params: Params | None = None) -> dict:
    """Everything behind one route's verdict: per-day trips and late counts, the trips nearest the late
    line, its worst trips, and its excluded trips with reason codes."""
    p = params or Params()
    res = L.evaluate(p)
    row = next((r for r in res["routes"] if r["route"] == route), None)
    if row is None:
        return {"error": f"no valid trips for {route} in scope"}
    _, valid, excluded, _ = L.load(p.trips_file)
    trips = [t for t in L.measure(valid, p)[0] if t["route"] == route]
    keep = ("trip_id", "scheduled_departure", "runtime_used_min", "actual_arrival", "lateness_min", "late")
    on_line = [{k: t[k] for k in keep} for t in trips if t["lateness_min"] == p.late_min]
    worst = sorted(trips, key=lambda t: -t["lateness_min"])[:10]
    ids = {r["trip_id"] for r in L.load(p.trips_file)[0] if r["route"] == route}
    runtime = dict(mean_timetabled_min=round(sum(t["runtime_used_min"] for t in trips) / len(trips), 2),
                   mean_actual_min=round(sum(t["actual_runtime_min"] for t in trips) / len(trips), 2),
                   median_actual_min=L.median(t["actual_runtime_min"] for t in trips))
    return redact(dict(**row, runtime=runtime, trips_exactly_on_line=on_line, worst_trips=[{k: t[k] for k in keep} for t in worst],
                       excluded=[dict(trip_id=t, reason=r) for t, r in excluded if t in ids]
                       + [dict(trip_id=t, reason=r) for t, r in p.exclude.items() if t in ids]))


@mcp.tool()
def trip(trip_id: str) -> dict:
    """One trip as the tool sees it: cleaned fields, lateness under default rules, or its exclusion reason."""
    rows, valid, excluded, converted = L.load()
    raw = next((r for r in rows if r["trip_id"] == trip_id), None)
    if raw is None:
        return {"error": f"{trip_id} not in export"}
    reason = dict(excluded).get(trip_id)
    fields = ("trip_id", "route", "vehicle_series", "scheduled_departure", "scheduled_runtime_min", "actual_arrival", "tz_offset")
    out = dict(raw_fields={k: raw[k] for k in fields}, excluded_reason=reason,
               converted=dict(converted).get(trip_id))
    if not reason:
        t = next(t for t in L.measure(valid, Params())[0] if t["trip_id"] == trip_id)
        out.update(lateness_min=t["lateness_min"], late=t["late"], actual_arrival_ist=t["actual_arrival"])
    return redact(out)


@mcp.tool()
def data_quality(trips_file: str = "assignment/data/trips.csv") -> dict:
    """Row counts, every excluded trip id grouped by reason code, converted rows, and trips per route."""
    rows, valid, excluded, converted = L.load(trips_file)
    by = {}
    for t, r in excluded:
        by.setdefault(r, []).append(t)
    per_route = {}
    for t in valid:
        per_route[t["route"]] = per_route.get(t["route"], 0) + 1
    return redact(dict(rows=len(rows), valid=len(valid), excluded={r: dict(count=len(ids), trip_ids=ids) for r, ids in by.items()},
                       converted=[dict(trip_id=t, reason=r) for t, r in converted],
                       trips_per_route=dict(min=min(per_route.values()), max=max(per_route.values()), routes=len(per_route))))


@mcp.tool()
def rec114_side_column(params: Params | None = None) -> dict:
    """Labelled side column, never a verdict: schedule_v2 routes measured under REC-114 (from its effective
    date, and for the whole week) next to the published-runtime basis, plus how many trips the 4xx
    vehicle-class selector can match in this export."""
    p = params or Params()
    hits = L.evaluate(p.model_copy(update={"rec114": "by_vehicle_class"}))["rec114"]["trips_remeasured"]
    return redact(dict(side_column=L.rec114_side_column(p),
                       vehicle_class_4xx="cannot be evaluated from this export: vehicle_series is a 2-digit field "
                                         f"(equal to the route number); trips selected: {hits}"))


@mcp.tool()
def ops_log() -> dict:
    """Ops-log lines by line number and category only (retention memo: no verbatim text). HANDOFF calls it
    last week's log (BRIEF and DATA_GUIDE say 'from the week'); it shares no key with trips.csv, so no verdict uses it."""
    return redact(dict(source="dated last week by HANDOFF, this week by BRIEF/DATA_GUIDE; no join key to trips.csv",
                       lines=L.ops_log()))


if __name__ == "__main__":
    mcp.run()
