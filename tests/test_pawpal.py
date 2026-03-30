"""
tests/test_pawpal.py — Core behavior tests for PawPal+
Run: python -m pytest
"""

from datetime import date, datetime, timedelta

import pytest

from pawpal_system import (
    DailySchedule,
    Owner,
    Pet,
    ScheduledTask,
    Scheduler,
    SchedulerConfig,
    Task,
    TaskStatus,
    TaskType,
    Priority,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_owner(minutes: int = 120) -> Owner:
    """Return a fresh Owner with one pet already attached."""
    owner = Owner(name="Alex", available_minutes_per_day=minutes)
    pet = Pet(name="Mochi", species="dog", owner_id=owner.owner_id)
    owner.add_pet(pet)
    return owner


def make_task(
    name: str = "Walk",
    priority: Priority = Priority.HIGH,
    duration: int = 30,
    pet_id: str = "pet-1",
    is_recurring: bool = False,
    recurrence_rule: str | None = None,
    due_datetime: datetime | None = None,
) -> Task:
    return Task(
        name=name,
        task_type=TaskType.WALK,
        priority=priority,
        duration_minutes=duration,
        pet_id=pet_id,
        is_recurring=is_recurring,
        recurrence_rule=recurrence_rule,
        due_datetime=due_datetime,
    )


def make_scheduled_task(
    name: str = "Walk",
    start: datetime | None = None,
    end: datetime | None = None,
    pet_id: str = "pet-1",
    priority: Priority = Priority.MEDIUM,
) -> ScheduledTask:
    """Return a ScheduledTask with explicit start/end times."""
    if start is None:
        start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    if end is None:
        end = start + timedelta(minutes=30)
    task = make_task(name=name, pet_id=pet_id, priority=priority)
    return ScheduledTask(task=task, start_time=start, end_time=end)


# ---------------------------------------------------------------------------
# Original tests (kept intact)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """mark_complete() should flip status from PENDING to COMPLETED."""
    task = make_task()
    assert task.status == TaskStatus.PENDING
    task.mark_complete()
    assert task.status == TaskStatus.COMPLETED


def test_add_task_increases_count():
    """add_task() should grow the pet's task list."""
    owner = make_owner()
    pet = owner.pets[0]
    assert len(pet.tasks) == 0
    pet.add_task(make_task(pet_id=pet.pet_id))
    assert len(pet.tasks) == 1
    pet.add_task(make_task(pet_id=pet.pet_id))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Behavior 1 — Urgency scoring
# ---------------------------------------------------------------------------

class TestUrgencyScoring:
    def test_critical_base_score(self):
        """CRITICAL priority alone should give a score of 4.0."""
        task = make_task(priority=Priority.CRITICAL)
        assert task.get_urgency_score() == 4.0

    def test_low_base_score(self):
        """LOW priority alone should give a score of 1.0."""
        task = make_task(priority=Priority.LOW)
        assert task.get_urgency_score() == 1.0

    def test_overdue_adds_ten(self):
        """An overdue task should gain a +10 bonus on top of its base score."""
        past = datetime.now() - timedelta(hours=1)
        task = make_task(priority=Priority.LOW, due_datetime=past)
        # LOW (1) + overdue bonus (10) = 11
        assert task.get_urgency_score() == 11.0

    def test_due_within_two_hours_adds_two(self):
        """A task due in < 2 hours (but not overdue) should gain +2."""
        soon = datetime.now() + timedelta(minutes=30)
        task = make_task(priority=Priority.LOW, due_datetime=soon)
        # LOW (1) + near-deadline bonus (2) = 3
        assert task.get_urgency_score() == 3.0

    def test_completed_overdue_task_no_bonus(self):
        """A completed task should not receive the overdue bonus."""
        past = datetime.now() - timedelta(hours=1)
        task = make_task(priority=Priority.LOW, due_datetime=past)
        task.mark_complete()
        # is_overdue() must return False for completed tasks
        assert not task.is_overdue()
        assert task.get_urgency_score() == 1.0


# ---------------------------------------------------------------------------
# Behavior 2 — Task prioritization
# ---------------------------------------------------------------------------

class TestPrioritizeTasks:
    def _scheduler(self) -> Scheduler:
        return Scheduler(owner=make_owner())

    def test_high_before_low(self):
        """HIGH priority task should be sorted before LOW priority task."""
        scheduler = self._scheduler()
        low = make_task(name="Groom", priority=Priority.LOW)
        high = make_task(name="Walk", priority=Priority.HIGH)
        result = scheduler.prioritize_tasks([low, high])
        assert result[0].priority == Priority.HIGH

    def test_overdue_low_beats_critical(self):
        """An overdue LOW task (score 11) should outrank a non-overdue CRITICAL (score 4)."""
        scheduler = self._scheduler()
        past = datetime.now() - timedelta(hours=2)
        overdue_low = make_task(name="Meds", priority=Priority.LOW, due_datetime=past)
        critical = make_task(name="Walk", priority=Priority.CRITICAL)
        result = scheduler.prioritize_tasks([critical, overdue_low])
        assert result[0].name == "Meds"

    def test_empty_list_returns_empty(self):
        """prioritize_tasks([]) should return [] without raising."""
        scheduler = self._scheduler()
        assert scheduler.prioritize_tasks([]) == []


# ---------------------------------------------------------------------------
# Behavior 3 — Greedy time-slot assignment
# ---------------------------------------------------------------------------

class TestFitTasksToWindow:
    def _scheduler(self, minutes: int = 120) -> Scheduler:
        return Scheduler(owner=make_owner(minutes=minutes))

    def test_all_tasks_fit_within_budget(self):
        """Two short tasks that fit within the budget should both be scheduled."""
        scheduler = self._scheduler(minutes=120)
        tasks = [
            make_task(name="Walk", duration=30),
            make_task(name="Feed", duration=20),
        ]
        result = scheduler.fit_tasks_to_window(tasks, 120)
        assert len(result) == 2

    def test_task_exceeding_budget_is_skipped(self):
        """A single task longer than available_minutes should not be scheduled."""
        scheduler = self._scheduler(minutes=10)
        tasks = [make_task(name="LongWalk", duration=999)]
        result = scheduler.fit_tasks_to_window(tasks, 10)
        assert len(result) == 0

    def test_buffer_gap_between_tasks(self):
        """
        The second task's start_time should equal the first task's end_time
        plus the configured buffer (default 10 min).
        """
        config = SchedulerConfig(buffer_minutes_between_tasks=10)
        scheduler = Scheduler(owner=make_owner(minutes=120), config=config)
        tasks = [
            make_task(name="Walk", duration=20),
            make_task(name="Feed", duration=20),
        ]
        result = scheduler.fit_tasks_to_window(tasks, 120)
        assert len(result) == 2
        expected_gap = result[0].end_time + timedelta(minutes=10)
        assert result[1].start_time == expected_gap

    def test_single_task_exact_budget(self):
        """A task that exactly fills the budget should be scheduled."""
        scheduler = self._scheduler(minutes=30)
        tasks = [make_task(name="Walk", duration=30)]
        result = scheduler.fit_tasks_to_window(tasks, 30)
        assert len(result) == 1

    def test_no_tasks_returns_empty(self):
        """fit_tasks_to_window with an empty list should return []."""
        scheduler = self._scheduler()
        assert scheduler.fit_tasks_to_window([], 120) == []


# ---------------------------------------------------------------------------
# Behavior 4 — Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def _schedule_with(self, *tasks: ScheduledTask) -> DailySchedule:
        schedule = DailySchedule(owner_id="owner-1", schedule_date=date.today())
        for st in tasks:
            schedule.scheduled_tasks.append(st)
        return schedule

    def _scheduler(self) -> Scheduler:
        return Scheduler(owner=make_owner())

    def test_no_overlap_returns_empty(self):
        """Tasks in non-overlapping slots should produce no conflicts."""
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        a = make_scheduled_task("Walk", start=base, end=base + timedelta(minutes=30))
        b = make_scheduled_task("Feed", start=base + timedelta(minutes=40), end=base + timedelta(minutes=60))
        schedule = self._schedule_with(a, b)
        conflicts = self._scheduler().check_conflicts(schedule)
        assert conflicts == []

    def test_exact_same_time_both_flagged(self):
        """Two tasks starting and ending at the same time should both be flagged."""
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        a = make_scheduled_task("Walk", start=base, end=base + timedelta(minutes=30))
        b = make_scheduled_task("Feed", start=base, end=base + timedelta(minutes=30))
        schedule = self._schedule_with(a, b)
        conflicts = self._scheduler().check_conflicts(schedule)
        assert len(conflicts) == 2
        assert a.is_conflict is True
        assert b.is_conflict is True

    def test_partial_overlap_both_flagged(self):
        """Tasks that partially overlap should both be marked as conflicts."""
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        a = make_scheduled_task("Walk", start=base, end=base + timedelta(minutes=30))
        b = make_scheduled_task("Feed", start=base + timedelta(minutes=15), end=base + timedelta(minutes=45))
        schedule = self._schedule_with(a, b)
        conflicts = self._scheduler().check_conflicts(schedule)
        assert len(conflicts) == 2

    def test_adjacent_tasks_no_conflict(self):
        """
        Task B starting exactly when task A ends should NOT conflict.
        conflicts_with() uses strict < so touching endpoints are allowed.
        """
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        a = make_scheduled_task("Walk", start=base, end=base + timedelta(minutes=30))
        b = make_scheduled_task("Feed", start=base + timedelta(minutes=30), end=base + timedelta(minutes=60))
        schedule = self._schedule_with(a, b)
        conflicts = self._scheduler().check_conflicts(schedule)
        assert conflicts == []

    def test_empty_schedule_no_conflicts(self):
        """An empty schedule should return no conflicts."""
        schedule = DailySchedule(owner_id="owner-1", schedule_date=date.today())
        conflicts = self._scheduler().check_conflicts(schedule)
        assert conflicts == []


# ---------------------------------------------------------------------------
# Behavior 5 — Recurring task generation
# ---------------------------------------------------------------------------

class TestRecurringTasks:
    def test_daily_task_creates_next_occurrence(self):
        """A daily recurring task should produce a new task due ~24 hours later."""
        task = make_task(is_recurring=True, recurrence_rule="daily")
        before = datetime.now()
        next_task = task.generate_next_occurrence()
        after = datetime.now()

        assert next_task is not None
        expected_low = before + timedelta(days=1)
        expected_high = after + timedelta(days=1)
        assert expected_low <= next_task.due_datetime <= expected_high

    def test_weekly_task_creates_next_occurrence(self):
        """A weekly recurring task should produce a new task due ~7 days later."""
        task = make_task(is_recurring=True, recurrence_rule="weekly")
        before = datetime.now()
        next_task = task.generate_next_occurrence()
        after = datetime.now()

        assert next_task is not None
        expected_low = before + timedelta(weeks=1)
        expected_high = after + timedelta(weeks=1)
        assert expected_low <= next_task.due_datetime <= expected_high

    def test_next_occurrence_inherits_properties(self):
        """The generated task should inherit name, type, priority, and pet_id."""
        task = make_task(
            name="Evening meds",
            priority=Priority.CRITICAL,
            pet_id="pet-42",
            is_recurring=True,
            recurrence_rule="daily",
        )
        next_task = task.generate_next_occurrence()
        assert next_task.name == "Evening meds"
        assert next_task.priority == Priority.CRITICAL
        assert next_task.pet_id == "pet-42"
        assert next_task.is_recurring is True

    def test_non_recurring_returns_none(self):
        """generate_next_occurrence() on a non-recurring task must return None."""
        task = make_task(is_recurring=False)
        assert task.generate_next_occurrence() is None

    def test_unknown_rule_returns_none(self):
        """An unrecognised recurrence_rule (e.g. 'monthly') should return None, not crash."""
        task = make_task(is_recurring=True, recurrence_rule="monthly")
        assert task.generate_next_occurrence() is None

    def test_recurring_flag_true_but_no_rule_returns_none(self):
        """is_recurring=True with recurrence_rule=None should return None gracefully."""
        task = make_task(is_recurring=True, recurrence_rule=None)
        assert task.generate_next_occurrence() is None


# ---------------------------------------------------------------------------
# Behavior 6 — Sorting correctness (DailySchedule)
# ---------------------------------------------------------------------------

class TestSorting:
    def _build_schedule(self) -> DailySchedule:
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        schedule = DailySchedule(owner_id="owner-1", schedule_date=date.today())
        # Add tasks out of chronological order on purpose
        schedule.scheduled_tasks = [
            make_scheduled_task("C-task", start=base + timedelta(hours=2), end=base + timedelta(hours=3), priority=Priority.LOW),
            make_scheduled_task("A-task", start=base, end=base + timedelta(hours=1), priority=Priority.CRITICAL),
            make_scheduled_task("B-task", start=base + timedelta(hours=1), end=base + timedelta(hours=2), priority=Priority.MEDIUM),
        ]
        return schedule

    def test_sort_by_time_chronological_order(self):
        """sort_by_time() must return tasks earliest-first."""
        schedule = self._build_schedule()
        sorted_tasks = schedule.sort_by_time()
        times = [st.start_time for st in sorted_tasks]
        assert times == sorted(times)

    def test_sort_by_time_does_not_mutate_original(self):
        """sort_by_time() should return a new list; original order unchanged."""
        schedule = self._build_schedule()
        original_first = schedule.scheduled_tasks[0].task.name
        schedule.sort_by_time()
        assert schedule.scheduled_tasks[0].task.name == original_first

    def test_sort_by_priority_critical_first(self):
        """sort_by_priority() must return CRITICAL task before LOW task."""
        schedule = self._build_schedule()
        sorted_tasks = schedule.sort_by_priority()
        assert sorted_tasks[0].task.priority == Priority.CRITICAL
        assert sorted_tasks[-1].task.priority == Priority.LOW

    def test_filter_by_pet_returns_correct_subset(self):
        """filter_by_pet() must return only tasks belonging to the requested pet."""
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        schedule = DailySchedule(owner_id="owner-1", schedule_date=date.today())
        schedule.scheduled_tasks = [
            make_scheduled_task("Walk", pet_id="pet-A"),
            make_scheduled_task("Feed", pet_id="pet-B"),
            make_scheduled_task("Groom", pet_id="pet-A"),
        ]
        result = schedule.filter_by_pet("pet-A")
        assert len(result) == 2
        assert all(st.task.pet_id == "pet-A" for st in result)

    def test_filter_by_pet_no_match_returns_empty(self):
        """filter_by_pet() with an unknown pet_id should return []."""
        schedule = DailySchedule(owner_id="owner-1", schedule_date=date.today())
        schedule.scheduled_tasks = [make_scheduled_task("Walk", pet_id="pet-A")]
        assert schedule.filter_by_pet("pet-Z") == []
