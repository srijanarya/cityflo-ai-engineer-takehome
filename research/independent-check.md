# Independent check of the data

Computed in a separate Claude session on 2026-10-09 with a standalone Python script that read the bundle's `trips.csv`. It had no access to this repo's code. The tool in this repo reproduces each number below, with one exception: R-33's p85 is 9.5 here and 9.55 in the tool, a percentile-method difference that changes no ranking. The session transcript shows those tool calls.

## Definitions used

- **Lateness** = (arrival converted to +05:30) − scheduled departure − `scheduled_runtime_min`, in minutes.
- **A late trip** arrives more than 5 minutes late.
- **A late route-day** has a strict majority of its valid trips late.
- **A LATE route** has a strict majority of its days late.

## Data

- **Rows:** 5,292 in total, of which 5,249 are valid.
- **Excluded:**
  - 24 UNPARSEABLE (arrival "…08:60");
  - 18 ARRIVAL_BEFORE_DEPARTURE (each arrives exactly 5 minutes before departure);
  - 1 DUPLICATE (T1-03237 repeats T1-03235).
- **Converted:** 1 TZ_CORRECTED (T1-02864, +00:00). It is kept.

## Routes, ranked by share of trips more than 5 minutes late

"Flip" is the number of trips that would have to change to reverse the verdict.

| Rank | Route | Valid trips | Late trips | % late | Median | p85 | Mean | Late days | Verdict | Flip |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | R-14 | 118 | 85 | 72.0 | 8.0 | 12.0 | 8.07 | 7/7 | LATE | 11 |
| 2 | R-33 | 104 | 49 | 47.1 | 5.0 | 9.5 | 5.36 | 2/7 | NOT LATE | 3 |
| 3 | R-26 | 103 | 44 | 42.7 | 4.0 | 8.0 | 4.51 | 3/7 | NOT LATE | 1 |
| 4 | R-37 | 105 | 42 | 40.0 | 4.0 | 8.0 | 4.13 | 1/7 | NOT LATE | 4 |
| 5 | R-31 | 112 | 37 | 33.0 | 4.0 | 7.0 | 3.59 | 0/7 | NOT LATE | 11 |

## Other checks

- **The mean misleads.** R-14's mean is 8.07 and R-35's is 8.05. R-35 is late on only 1 of 7 days.
- **R-35's Wednesday (2026-08-05):**
  - 19 trips, mean 51.3 minutes late, range 36–61.
  - R-35's other days: 113 trips, mean 0.78.
  - It is the only route-day whose median lateness is above 15 minutes.
- **Trips more than 15 minutes late:** 29 in total. R-35 has 19, R-14 8, R-08 1 and R-09 1.
- **Other line choices:**
  - With "5 minutes or more" as the late-trip line, the majority rule flags R-14, R-26 and R-33.
  - The agent's first rule (weekly median ≥ 5 and at least 4 daily medians ≥ 5) flags R-14 and R-33.
- **Industry-style targets:**
  - Routes under 80% on time: 17.
  - Routes under 75% on time: 6.
  - The median route has 16.7% of trips late.
- **REC-114 applied to R-14** (revised runtime of 53 minutes):
  - From 2026-08-05: 51 of 118 trips late, 2 of 7 days late.
  - For the whole week: 37 of 118 trips late, 0 of 7 days late.
  - R-14's mean scheduled runtime is 45.25, and its mean lateness is 8.07.
