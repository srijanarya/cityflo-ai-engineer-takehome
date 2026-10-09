# Route lateness, week of 3–9 Aug 2026: decision record

**For:** Priya, Ops Lead (Mumbai North), Friday regional review.

*The calls below are Srijan's, made after walking through each one with a separate research session that supplied several of the arguments (see README, "How this was made").*

**Answer: one route was late this week, R-14.**

**Worst three:**

| Rank | Route | Verdict | Trips more than 5 min late | Median lateness (min) | p85 (min) |
|---|---|---|---|---|---|
| 1 | R-14 | LATE | 72.0% | 8.0 | 12.0 |
| 2 | R-33 | NOT LATE | 47.1% | 5.0 | 9.55 |
| 3 | R-26 | NOT LATE | 42.7% | 4.0 | 8.0 |

- **Watch list.** Three NOT LATE routes are within 4 trips of LATE: R-26 (1 trip), R-33 (3) and R-37 (4).
- **Refund queue.** 29 trips more than 15 minutes late go to refund review.
- **Incident.** R-35's Wednesday is flagged as an incident.

**Least-sure call: the late line (call 1).** R-26 is one trip from LATE, and three of its Monday trips stamped exactly 5:00 decide it.

**What R-14's LATE means.** R-14 was late against the timetable its riders were given. That is **not a finding that the depot is at fault.** R-14's buses take about 53 minutes, and the timetable says about 45. **Before Friday, Priya should ask the timetable owner one question:** was the 53-minute R-14 timetable published to riders from 5 Aug? If it was, R-14 is NOT LATE (call 3).

Every number below comes from the `cityflo-lateness` MCP server, called in the session transcript. The only exceptions are the checks marked "(code)", which ran the same module from a script. Re-run any number with `route_verdicts`, `route_detail`, `what_if`, `trip` or `data_quality`.

**Data used:** 5,292 rows; 5,249 used. 43 were excluded with a reason code, and 1 was converted and kept (call 6). The per-route table is at the bottom. **Flip** is the number of trips whose late/on-time status would have to change to reverse that route's verdict.

---

## 1. The late line: what makes a trip, a day and a route late

**The rule.**
- **Trip:** lateness = actual arrival (converted to +05:30) − (scheduled departure + `scheduled_runtime_min`). A trip is late if lateness is **more than 5 minutes**. Arriving early counts as on time.
- **Day:** a route-day is late if **more than half** of its valid trips are late.
- **Route:** a route is **LATE** if **more than half of the days in scope** are late, which is 4 or more of 7. Every route gets LATE or NOT LATE.
- **Thin data:** a route with fewer than 3 days of data, or any day with fewer than 5 valid trips, is tagged `low_confidence`. No route is tagged this week.
- **Ties:** a tie at the clock's resolution goes to NOT LATE, at both levels.

**Why this line.**
- **5 minutes is the standard on-time window:** 0 to 5 in TCQSM, +5 at TfL, and 5:59 in Ireland's tendered-bus contracts.
- **India's CESL e-bus contract is in the same range.** Its window is 10% of trip time, which is about 4.5 minutes on a 45-minute trip.
- **Devices stamp whole minutes**, so a reading of 5:00 is within clock error. The depot bonus is all-or-nothing for one person, so the evidence against a depot has to be clear.
- **Early arrivals count as on time, unlike TCQSM.** An office commuter who arrives early isn't harmed.
- **Why the day-majority rule.** It measures persistence: how many days riders could not rely on the route. A pooled share of trips over the whole week can't tell one terrible day from a week of mild lateness, and call 4 shows that difference matters.

**Where it breaks: R-26 (flip 1).**
- **Monday 3 Aug decides it.** R-26 has 14 valid trips that day, and exactly 7 are late. That's half, so it isn't a late day, and R-26 ends the week at 3 of 7 late days: NOT LATE.
- **Three Monday trips sit exactly on the line**, at 5.0 minutes: **T1-03292, T1-03296 and T1-03298**. Count any one of them as late and R-26 is LATE.
- **An excluded row could flip it too.** T1-03297 runs on that same Monday, and its arrival is the unreadable "08:60" (see call 6).
- **I'm keeping the rule.** The alternative treats a 5:00 stamp as proof of lateness, which the clock can't support.

**Where it breaks: R-33 (flip 3).** R-33 is late on 2 of 7 days. If 5:00 counts as late, it becomes **6 of 7**, the biggest swing of any route. Its trips cluster right at the line.

**The cost, and who pays.**
- **Riders on the three watch-list routes** (R-26, R-33, R-37) rode **135 trips more than 5 minutes late** this week. None of those trips is in the refund queue, so they get no remedy.
- **If 5:00 counted as late** (`what_if late_inclusive=true`), R-33 (2/7 → 6/7 days) and R-26 (3/7 → 4/7) both become LATE. The LATE list goes from 1 route to 3, and two more depot heads lose their incentive on whole-minute stamps.

**What would change my mind.** Either of these would make me switch to `late_inclusive=true`, which makes R-26 and R-33 LATE:
- the device team shows its clocks are accurate to well under a minute;
- the review formally adopts "5:00 is late".

## 2. The worst-three ranking

**The rule.** Rank routes by the **share of their valid trips more than 5 minutes late**. Break ties by p85 lateness, then by route id. This uses the same unit as the verdict, and it is separate from it: the worst three is where ops looks first, while LATE is the line with money attached.

**Where it breaks: R-35.**
- R-35 has the second-worst tail of any route (p85 11.35) and the second-highest mean (8.05; R-14's is 8.07).
- Ranked by mean or by p85 (`what_if rank_by=mean` or `rank_by=p85`), the worst three becomes **R-14, R-35, R-33**.
- Under my rule R-35 ranks **7th**, at 24.2% of trips late, because its whole tail is one day (call 4). On its other six days the mean is 0.78, and 13 of 113 trips are late.
- I'm keeping the rule, because a single day shouldn't set a weekly ranking. R-35's riders are covered by the refund queue instead.

**Third place is the weakest spot.**
- **With 5:00 on time:** R-26 has 44 late trips out of 103 and R-37 has 42 out of 105. R-37 would pass R-26 with **3** more late trips.
- **With 5:00 late:** R-26 has 51 out of 103 and R-37 has 50 out of 105, a margin of **2** trips (code, from tool counts).

**The cost, and who pays.**
- **Ranking itself carries no penalty, but it is public.** R-33's and R-26's depot heads are named in the review's worst three without being LATE, so their reputations take the hit even though their bonuses don't.
- If R-35's Wednesday was a depot failure, my rule keeps R-35 out of that spotlight.

**What would change my mind.**
- **The review cares about worst-case trips more than typical days.** Then I'd rank by p85, which puts R-35 2nd.
- **A second R-35 incident day.** Then the tail is a pattern, not a one-off.

## 3. REC-114: not applied to any verdict

**The rule.** Measure every trip against the runtime riders were given, which is `scheduled_runtime_min` in the export. Schedule_v2 is shown only as a **labelled side column** (`rec114_side_column`).

**Why.**
- **It is circular, and this is the main reason.** Applied by route, REC-114 lands on R-14, the one LATE route. Its revised 53 minutes is R-14's actual typical trip (mean 53.32, median 53.0, against a timetabled mean of 45.25). Measuring a route against its own performance erases its lateness by construction.
- **Its stated purpose is the wrong one.** "So the numbers line up with what the review already has" means fitting the answer to an expected figure.
- **Its selector can't be checked.** The **4xx vehicle selector cannot be evaluated from this export**: `vehicle_series` is a two-digit field and equals the route number on every row.

**Where it breaks: R-27.** Schedule_v2 lists R-27 at 45 minutes with the note "no change". R-27's published runtimes vary from trip to trip, so a flat 45 isn't a no-op:

| | As published (the verdict basis) | REC-114 from 5 Aug | REC-114 whole week |
|---|---|---|---|
| R-14 | 85 / 118 late, 7/7 days, **LATE** | 51 / 118, 2/7 days, NOT LATE | 37 / 118, 0/7 days, NOT LATE |
| R-27 | 32 / 143 late, 0/7 days, NOT LATE | 62 / 143, 3/7 days, NOT LATE | 67 / 143, 3/7 days, NOT LATE |

**The cost, and who pays.**
- **The R-14 depot head loses the on-time incentive.** Under REC-114 they would keep it.
- **Priya takes on a dispute with ops-automation**, who signed REC-114 off.
- **Recommendation:** publish 53 minutes as R-14's timetable from next week.

**What would change my mind.** Proof that riders were shown the 53-minute timetable from 5 Aug. Then I'd apply it to R-14 from that date only: 51 of 118 late, 2 of 7 days, and **R-14 becomes NOT LATE**. No route would then be LATE this week. That is the question for the timetable owner, above.

## 4. R-35's Wednesday (5 Aug): kept, flagged, refunded and sent for checking

**The rule.**
- **Never trim a row for being extreme.**
- **Flag incidents.** A route-day whose median lateness is above 15 minutes is flagged as an incident. Its trips stay in every number, go to refund review and are sent to the device team to check.
- **This week exactly one route-day qualifies:** R-35 on 5 Aug. All 19 of its trips are late, by 36 to 61 minutes (mean 51.3, median 52), with departures from 06:35 to 20:21.

**R-35 is NOT LATE.** One bad day out of 7 doesn't meet the majority rule. Its flip is 21 trips.

**The ops log isn't used, though the sources disagree about its date.**
- HANDOFF calls it *last week's* log. BRIEF and DATA_GUIDE describe it as notes "from the week".
- **The call doesn't rest on the date. It rests on two other facts:**
  - **The log has no join key to trips.**
  - **Its diversion line doesn't match R-35's day.** The log reads about 35 minutes, mornings, a whole western corridor. R-35's day was about 51 minutes, all day, one route.
- **No other route was hit on Wednesday morning.** R-35's 06:00–11:00 median was 48.5 minutes. No other route had a median above 15 that morning, and no other route-day has one across a full day.

**Where it breaks: R-35 itself.** If the day was real and the depot's fault, the rule lets that depot head escape a penalty for the worst single day in the data. I'm keeping the rule anyway. Under a one-bad-day standard, any depot could lose its bonus to a single device fault.

**The cost, and who pays.**
- **If it was a depot failure:** the R-35 depot head keeps an incentive they arguably lost.
- **If it was a device fault:** the refund owner reviews **19 trips that were actually on time**. That is 19 of the queue's 29 entries.

**What would change my mind.** A second time source showing those trips ran on time, such as conductor logs, ticket scans or another GPS unit. Then I'd exclude them with a reason code (`exclude={trip_id: "SECOND_TIME_SOURCE"}`), which takes the refund queue from 29 trips to 10.

## 5. The refund queue: more than 15 minutes late, whatever the route verdict

**The rule.** Any trip more than 15 minutes late goes to the refund queue, whatever its route's verdict. The refund owner decides on each trip, not us. The queue is sized in trips only: there are no fares or loads in the data, so there are no rupee figures.

**Why 15 is a judgment call.** It is **three times the late line**, and it keeps the queue at **29** trips, a number someone can review. CESL's 15 minutes is only the cap on its on-time window, not a refund standard. Cityflo's own subscription policy publishes no lateness refund.

**This week:** 29 trips. 21 of them are on NOT LATE routes, so riders who were badly late are covered even where the depot verdict is strict.

**Where it breaks: the 15-minute line itself.** **7 trips are exactly 15.0 minutes late** and fall outside the queue. `refund_min=14` would take the queue to 36.

**The cost, and who pays.**
- **The refund owner** gets 29 reviews, 19 of them from one incident day.
- **Riders 10–15 minutes late get nothing:** that's **108 trips** (`refund_min=10` would make the queue 137).
- **The 135 late trips on the watch-list routes** (call 1) get no remedy either.

**What would change my mind.** A published Cityflo refund policy, or fare and load data that lets the threshold be set by cost.

## 6. Bad rows: what's removed, and the one that's converted

**The rule.** Remove only rows that cannot be true, each with a reason code:
- **UNPARSEABLE (24):** the arrival is stamped "…08:60".
- **ARRIVAL_BEFORE_DEPARTURE (18):** each one is exactly 5 minutes before departure (code).
- **DUPLICATE (1):** T1-03237 repeats T1-03235's route, departure and arrival.

One row is converted and kept: **TZ_CORRECTED (1)**, T1-02864, stamped +00:00. Converted to +05:30 it arrives 2 minutes early.

**"08:60" isn't a rollover to 09:00.** Departures run from 06:00 to 21:59. Read as 09:00, 21 of the 24 rows would arrive before they departed, and none would land within 15 minutes of schedule (code).

**The worst case on the watch-list routes.** If every excluded row on these routes were counted as a late trip (code):

| Route | Excluded rows | Late days: now → worst case | Verdict in the worst case |
|---|---|---|---|
| R-26 | 2 (T1-03297 UNPARSEABLE, Mon 3 Aug; T1-03377 ARRIVAL_BEFORE_DEPARTURE, Sun 9 Aug) | 3/7 → 4/7 | **LATE** |
| R-33 | 1 (T1-04337 UNPARSEABLE) | 2/7 → 2/7 | NOT LATE |
| R-37 | 0 | 1/7 → 1/7 | NOT LATE |

Only R-26 flips. The flip comes through Monday, via T1-03297, the same day the 5:00 tie decides.

**Where it breaks: the duplicate pair isn't an exact copy.** T1-03235 has a 45-minute runtime and T1-03237 has 40. The kept row reads 1 minute early, and the dropped one would read 4 minutes late. Neither is late, so no verdict depends on which is kept.

**The cost, and who pays.** The 18 arrival-before-departure rows look like a systematic device fault. If those trips ran late, the affected routes' late counts are understated by one trip per row. On the watch list, that risk only reaches R-26.

**What would change my mind.** The device team recovering true arrival times. Specifically, T1-03297 arriving more than 5 minutes late would make R-26 LATE.

---

## Per-route table

Sorted by route. **Rank** is the worst-three order (by share late, then p85). **Late days** counts route-days where more than half the trips are late.

| Route | Verdict | Late days | Trips | Late trips | % late | Median (min) | p85 (min) | Flip | Rank |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | **NOT LATE** | 0/7 | 153 | 13 | 8.5 | 1.0 | 5.0 | 36 | 34 |
| R-02 | **NOT LATE** | 0/7 | 105 | 15 | 14.3 | 2.0 | 5.0 | 20 | 27 |
| R-03 | **NOT LATE** | 0/7 | 103 | 21 | 20.4 | 2.0 | 6.0 | 17 | 17 |
| R-04 | **NOT LATE** | 0/7 | 144 | 14 | 9.7 | 0.0 | 4.0 | 33 | 33 |
| R-05 | **NOT LATE** | 0/7 | 105 | 20 | 19.0 | 2.0 | 6.4 | 17 | 18 |
| R-06 | **NOT LATE** | 0/7 | 117 | 6 | 5.1 | -2.0 | 3.0 | 30 | 38 |
| R-07 | **NOT LATE** | 0/7 | 147 | 32 | 21.8 | 3.0 | 6.0 | 20 | 11 |
| R-08 | **NOT LATE** | 0/7 | 126 | 26 | 20.6 | 3.0 | 6.0 | 21 | 16 |
| R-09 | **NOT LATE** | 0/7 | 146 | 33 | 22.6 | 2.0 | 6.25 | 20 | 8 |
| R-10 | **NOT LATE** | 0/7 | 126 | 18 | 14.3 | 1.0 | 5.0 | 25 | 28 |
| R-11 | **NOT LATE** | 0/7 | 137 | 23 | 16.8 | 2.0 | 6.0 | 24 | 20 |
| R-12 | **NOT LATE** | 0/7 | 112 | 15 | 13.4 | 2.0 | 5.0 | 25 | 29 |
| R-13 | **NOT LATE** | 0/7 | 133 | 8 | 6.0 | -1.0 | 3.0 | 33 | 37 |
| R-14 | **LATE** | 7/7 | 118 | 85 | 72.0 | 8.0 | 12.0 | 11 | 1 |
| R-15 | **NOT LATE** | 1/7 | 119 | 25 | 21.0 | 3.0 | 6.3 | 16 | 13 |
| R-16 | **NOT LATE** | 0/7 | 146 | 7 | 4.8 | 0.0 | 4.0 | 38 | 39 |
| R-17 | **NOT LATE** | 1/7 | 147 | 41 | 27.9 | 3.0 | 7.0 | 15 | 6 |
| R-18 | **NOT LATE** | 0/7 | 154 | 32 | 20.8 | 2.0 | 6.0 | 26 | 15 |
| R-19 | **NOT LATE** | 0/7 | 125 | 23 | 18.4 | 3.0 | 6.0 | 19 | 19 |
| R-20 | **NOT LATE** | 0/7 | 145 | 24 | 16.6 | 2.0 | 6.0 | 27 | 21 |
| R-21 | **NOT LATE** | 0/7 | 124 | 26 | 21.0 | 2.0 | 6.0 | 20 | 14 |
| R-22 | **NOT LATE** | 0/7 | 112 | 18 | 16.1 | 2.0 | 6.0 | 22 | 24 |
| R-23 | **NOT LATE** | 0/7 | 132 | 8 | 6.1 | 0.0 | 4.0 | 34 | 36 |
| R-24 | **NOT LATE** | 0/7 | 146 | 16 | 11.0 | 1.0 | 4.25 | 31 | 30 |
| R-25 | **NOT LATE** | 0/7 | 138 | 20 | 14.5 | 1.0 | 5.0 | 26 | 26 |
| R-26 | **NOT LATE** | 3/7 | 103 | 44 | 42.7 | 4.0 | 8.0 | 1 | 3 |
| R-27 | **NOT LATE** | 0/7 | 143 | 32 | 22.4 | 2.0 | 7.0 | 22 | 10 |
| R-28 | **NOT LATE** | 0/7 | 151 | 15 | 9.9 | 1.0 | 4.0 | 34 | 31 |
| R-29 | **NOT LATE** | 0/7 | 151 | 6 | 4.0 | -1.0 | 3.0 | 41 | 40 |
| R-30 | **NOT LATE** | 0/7 | 147 | 11 | 7.5 | -1.0 | 4.0 | 34 | 35 |
| R-31 | **NOT LATE** | 0/7 | 112 | 37 | 33.0 | 4.0 | 7.0 | 11 | 5 |
| R-32 | **NOT LATE** | 0/7 | 133 | 21 | 15.8 | 1.0 | 6.0 | 26 | 25 |
| R-33 | **NOT LATE** | 2/7 | 104 | 49 | 47.1 | 5.0 | 9.55 | 3 | 2 |
| R-34 | **NOT LATE** | 0/7 | 124 | 28 | 22.6 | 3.0 | 7.0 | 16 | 9 |
| R-35 | **NOT LATE** | 1/7 | 132 | 32 | 24.2 | 2.0 | 11.35 | 21 | 7 |
| R-36 | **NOT LATE** | 0/7 | 132 | 13 | 9.8 | 1.0 | 4.0 | 30 | 32 |
| R-37 | **NOT LATE** | 1/7 | 105 | 42 | 40.0 | 4.0 | 8.0 | 4 | 4 |
| R-38 | **NOT LATE** | 0/7 | 146 | 24 | 16.4 | 1.0 | 6.0 | 28 | 22 |
| R-39 | **NOT LATE** | 0/7 | 154 | 25 | 16.2 | 2.0 | 6.0 | 30 | 23 |
| R-40 | **NOT LATE** | 0/7 | 152 | 33 | 21.7 | 3.0 | 6.0 | 25 | 12 |
