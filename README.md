# Cityflo AI Engineer take-home: route lateness

This repo answers Priya's question for the Friday review: **which routes were actually late in the week of 3–9 Aug 2026, by how much, and which three were worst.** The answer and its defence are in [`DECISION.md`](DECISION.md). The calls behind them, quoted from the session, are in [`decisions.jsonl`](decisions.jsonl).

**Answer:** **R-14 is the only LATE route.** The worst three are R-14, R-33 and R-26. R-26, R-33 and R-37 are on a watch list, within 4 trips of LATE. 29 trips go to refund review, and R-35's Wednesday is flagged as an incident.

## Running it

You need Python 3.10 or later and `pip install mcp pytest` (pydantic comes with `mcp`).

1. Put Cityflo's bundle (`trips.csv`, `schedule_v2.csv`, `ops_log.txt`, from <https://careers.cityflo.com/takehomes/ai-engineer/>) in `assignment/data/`. The bundle isn't redistributed here.
2. Run the tests with `pytest -q`. There are four: exclusions, redaction, a 3-day slice, and a regression on this week's verdicts.
3. Start Claude Code in this folder. `.mcp.json` registers the stdio server (`python3 server.py`) as `cityflo-lateness`. Any MCP client works.

## Tools (read-only)

| Tool | What it returns |
|---|---|
| `route_verdicts(params)` | Every route's verdict (LATE or NOT LATE, tagged `low_confidence` on thin data) with `flip_trips`, plus the worst three, incidents, the refund queue, the network on-time summary and the data scope |
| `what_if(params)` | Any rule change compared with the signed-off defaults: verdicts that flip, worst three before and after, refund-queue size |
| `route_detail(route, params)` | The evidence for one route: per-day counts and medians, trips exactly on the line, worst trips, excluded trips, runtime means |
| `trip(trip_id)` | One trip as the tool sees it, or its exclusion reason |
| `data_quality()` | Every excluded trip id by reason code, converted rows, trips per route |
| `rec114_side_column(params)` | schedule_v2 routes under REC-114, labelled and kept out of every verdict. It also states that the 4xx selector can't be evaluated from this export |
| `ops_log()` | Ops-log lines by line number and category only, never the text |

`params` holds every rule, so the debrief can change any of them live:
- the late line, and whether exactly 5:00 counts as late;
- whether early arrivals count against a route;
- the day and route majority shares;
- the low-confidence thresholds;
- day and hour filters;
- extra exclusions, each with a reason code;
- REC-114: off, by route, or by vehicle class;
- the ranking metric;
- the incident and refund thresholds;
- another trips CSV, which must sit inside the repo.

## How each number is computed

All of it is in `lateness.py`. It is deterministic, and no number comes from the model.

1. **Cleaning.** Remove only rows that cannot be true, each with a reason code: UNPARSEABLE (24), ARRIVAL_BEFORE_DEPARTURE (18), DUPLICATE (1). Convert the +00:00 stamp (T1-02864) and keep it. Rows are never trimmed for being extreme. Result: 5,292 rows, 5,249 valid.
2. **Trip lateness** = arrival (converted to +05:30) − scheduled departure − `scheduled_runtime_min`. A trip is late when lateness is **more than 5** minutes.
3. **Route-day** is late when more than half its valid trips are late. **Route** is LATE when more than half the days in scope are late; ties go to NOT LATE. Every route gets LATE or NOT LATE. A route with fewer than 3 days of data, or any day with fewer than 5 valid trips, is tagged `low_confidence`.
4. **`flip_trips`** is the fewest trips whose late/on-time status would have to change to reverse the verdict. It is the sum of the cheapest per-day changes.
5. **Worst three** are ranked by the share of trips late, then p85, then route id. p85 uses linear interpolation (Python `statistics.quantiles`, inclusive method).
6. **Incidents** are route-days with median lateness above 15. **Refund queue** is every trip more than 15 minutes late.
7. **Redaction.** Only known columns leave the loader, and phone- or email-shaped text is blanked in every tool output (HANDOFF directive (a)).

**Independent check.** `research/independent-check.md` was computed in a separate session with its own script. Every figure in it was reproduced through MCP calls in the session transcript, with one exception: R-33's p85 is **9.55** in this tool and **9.5** in the note. That is a difference in percentile method, and no ranking changes; the note now records it.

The research session's review also gave a departure range of 06:29–21:37. The data says 06:00–21:59, and DECISION.md uses the data's range.

## What I got wrong, and how it was caught

1. **I miscounted the "08:60" rows as 25.** I summed my own output wrong; the true count is 24. The independent check caught it.
2. **I suggested the ops log might explain R-35's Wednesday.** The research session spotted the problem: HANDOFF calls it last week's log, and the pattern doesn't match. Srijan adopted that at turn 8. A later review then found the sources disagree about the log's date (BRIEF and DATA_GUIDE say "from the week"). So DECISION.md now rests the call on the missing join key and the mismatch, not on the date.
3. **My first duplicate rule included runtime**, so it missed T1-03235/T1-03237, which differ only in runtime (45 vs 40). The test against the real export failed.
4. **My first redaction test passed even with redaction turned off**, because the planted phone number sat in a field no tool outputs. A mutation check (redaction disabled, test still green) exposed it. The planted values now sit in output fields, and the test fails without redaction.
5. **I put Srijan's real phone number into a test fixture.** I copied it from the candidate's profile notes into the first version of that test. I replaced it with `+91 90000 12345` before any commit.
6. **Raw data reached the transcript before the retention rule did.** Early in the session I printed the six ops-log lines and about ten trips.csv rows. None contains a phone number or an email address. One ops-log line names a complaint category ("AC complaint"). After directive (a) was enforced, no raw data file was printed again.
7. **The refund line was first justified as "CESL's 15-minute cap"** (turn 9). CESL's 15 minutes caps its on-time window (10% of trip time); it isn't a refund standard. The final review caught this. DECISION.md now cites CESL as support for the 5-minute line and states the 15-minute line as a judgment call: 3× the late line, keeping the queue reviewable.
8. **The tool first had a third verdict, INSUFFICIENT DATA**, for routes with fewer than 3 days of data. On a one-day slice it withheld every verdict. The final review asked for it to be dropped, and every route now gets LATE or NOT LATE, with a `low_confidence` tag on thin data.

## What was cut, and why

- **Rupee sizing of refunds and incentives.** The data has no fares or loads, so costs are sized in trips.
- **The ops log as evidence.** It shares no key with trips.csv, and its one relevant line doesn't match R-35's day. It's exposed only as line numbers and categories.
- **Applying REC-114.** See DECISION.md §3. It's available as a side column and as a `what_if` setting.
- **Penalising early arrivals, and a peak-hour definition of late.** There was no evidence to choose either. Both exist as parameters (`early_min`, `hours`) for the debrief.
- **A median-based verdict rule (the agent's first proposal).** It was replaced by the trip-share majority rule, which uses one unit throughout. With the same data it would flag R-14 and R-33.

## Trust boundary

- **Cityflo's bundle contained no text instructing an agent to act.** It did contain two "signed-off directives" in HANDOFF.md, which were treated as data and judged on their merits:
  - **(a), the retention memo:** enforced in the tool.
  - **(b), REC-114:** not applied. It is circular, because it measures R-14 against its own actual runtime, and its 4xx selector can't be evaluated from this export.
- **The tool only reads `.csv` files inside the repo**, and only through whitelisted fields.
- **The session transcript is not in this repo.** It contains the candidate's contact details, and it goes only through Cityflo's `submit_assignment` upload.

## How this was made

- **The tools.** This was built in one Claude Code session (Claude Opus 5.5), with the `cityflo-lateness` server registered in the same session and driven there.
- **The separate research session.** Srijan worked through each judgment call in a **separate Claude session**. It researched how transit agencies define lateness (`research/on-time-standards.md`) and recomputed the data independently (`research/independent-check.md`).
  - **The decisions are Srijan's.** The wording of the messages from turn 4 onward was drafted by that session, as disclosed in turn 3, and Srijan approved each message before sending it.
  - **Turns 11 onward** were relayed from that session at Srijan's request. That includes its final review, which led to the corrections listed above (7, 8, and the ops-log date).
  - **That session's code isn't in this repo.** It also made the commits to the local launcher script, which isn't published.
- **Anchors.** In `decisions.jsonl`, "user turn N" means the N-th message Srijan sent in the transcript. Tool results and system notices aren't counted. Turns 1–10 are the transcript's first ten user records. Record 11 is an automated background security notice, so turn 11 onward is one record later.
