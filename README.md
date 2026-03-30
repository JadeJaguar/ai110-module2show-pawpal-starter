# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

Phase 4 added an algorithmic layer on top of the core scheduler. Here is what is now supported:

**Sorting**
- `DailySchedule.sort_by_time()` — returns the day's tasks ordered by start time (earliest first), using a `lambda` key on `datetime` objects so no string parsing is needed.
- `DailySchedule.sort_by_priority()` — returns tasks ordered by priority value (CRITICAL → LOW), using `reverse=True` on the numeric enum backing so the most urgent tasks always appear at the top.

**Filtering**
- `DailySchedule.filter_by_pet(pet_id)` — isolates one animal's tasks from a multi-pet schedule without regenerating the plan.
- `DailySchedule.filter_by_status(status)` — lets the UI separate completed, scheduled, and skipped tasks at a glance.

**Recurring tasks**
- Tasks can be flagged `is_recurring=True` with a `recurrence_rule` of `"daily"` or `"weekly"`.
- When a recurring task is marked complete, `Task.generate_next_occurrence()` automatically creates a fresh `PENDING` copy with `due_datetime` set via `timedelta` (today + 1 day or today + 7 days).
- The Streamlit UI shows a toast notification when a next occurrence is queued.

**Conflict detection**
- `Scheduler.check_conflicts(schedule)` runs an O(n²) pairwise overlap check across all scheduled tasks.
- Conflicting tasks are flagged with `is_conflict=True` and a warning banner appears in the UI listing each overlapping pair.
- Conflicts are re-checked live whenever the user manually overrides a task's start time, so problems are surfaced immediately.

**UI improvements added alongside the algorithmic layer**
- Checkbox per task to mark it complete directly from the schedule view.
- Time override input per task to adjust the generated start time without regenerating the whole schedule.
- Optional preferred time when adding a task, stored as a `TimeWindow` on `task.preferred_window`.
- Multi-pet support: multiple pets can be registered to one owner, and tasks are assigned to a chosen pet via a dropdown.

---

## Testing PawPal+

### Run the tests

```bash
python -m pytest        # quick pass/fail summary
python -m pytest -v     # verbose — shows every test name and result
```

### What the tests cover

The test suite in `tests/test_pawpal.py` contains **31 tests** across 6 behavioral groups:

| Group | Tests | What it verifies |
|-------|-------|-----------------|
| **Urgency scoring** | 5 | Base priority scores, +10 overdue bonus, +2 near-deadline bonus, completed tasks don't get overdue bonus |
| **Task prioritization** | 3 | High-priority tasks sort before low, overdue low task outranks fresh critical, empty list handled safely |
| **Greedy scheduling** | 5 | Tasks fit within time budget, oversized tasks are skipped, 10-min buffer applied between tasks, edge case of exact-fit budget |
| **Conflict detection** | 5 | Non-overlapping tasks produce no conflicts, exact-same-time tasks both flagged, partial overlap flagged, adjacent tasks (touching endpoints) are not conflicts, empty schedule handled |
| **Recurring tasks** | 6 | Daily rule creates task due tomorrow, weekly rule creates task due in 7 days, new task inherits all properties, non-recurring returns None, unknown rule returns None gracefully |
| **Sorting & filtering** | 5 | `sort_by_time()` returns chronological order, sort doesn't mutate original list, `sort_by_priority()` puts CRITICAL first, `filter_by_pet()` returns correct subset, unknown pet returns empty list |

### Confidence level

**4 / 5 stars**

All 31 tests pass and cover the core scheduling logic end-to-end — urgency scoring, greedy time assignment, conflict detection, and recurring task generation. The main gap is that the tests run against in-memory state only; there are no integration tests for the Streamlit UI layer or for the `respect_preferred_windows` scheduling path (which is configured but not yet enforced). Those two areas are where surprises could still appear in production.

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
