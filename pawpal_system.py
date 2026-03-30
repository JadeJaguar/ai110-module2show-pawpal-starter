"""
PawPal+ — Backend Logic Layer
All core classes live here: enums, data models, scheduler, and supporting services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TaskType(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    GROOMING = "grooming"
    VET_APPOINTMENT = "vet_appointment"
    ENRICHMENT = "enrichment"
    TRAINING = "training"
    OTHER = "other"


class Priority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class TaskStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    OVERDUE = "overdue"


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

@dataclass
class TimeWindow:
    label: str
    start_time: time
    end_time: time
    days_of_week: list[str] = field(default_factory=list)  # e.g. ["Mon", "Wed"]
    is_active: bool = True

    def contains(self, dt: datetime) -> bool:
        """Return True if the given datetime falls within this window."""
        return self.start_time <= dt.time() < self.end_time

    def duration_minutes(self) -> int:
        """Return the length of this window in minutes."""
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        return int((end_dt - start_dt).total_seconds() // 60)

    def overlaps(self, other: TimeWindow) -> bool:
        """Return True if this window overlaps with another."""
        return self.start_time < other.end_time and self.end_time > other.start_time


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    name: str
    task_type: TaskType
    priority: Priority
    duration_minutes: int
    pet_id: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    preferred_window: Optional[TimeWindow] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None   # e.g. "daily", "weekly"
    due_datetime: Optional[datetime] = None
    notes: str = ""

    def mark_complete(self) -> None:
        """Set status to COMPLETED."""
        self.status = TaskStatus.COMPLETED

    def generate_next_occurrence(self) -> Optional[Task]:
        """If this task is recurring, return a new Task instance for the next occurrence.

        recurrence_rule="daily"  → due_datetime = now + 1 day
        recurrence_rule="weekly" → due_datetime = now + 7 days
        Returns None if the task is not recurring or the rule is unrecognised.
        """
        if not self.is_recurring or not self.recurrence_rule:
            return None

        rule = self.recurrence_rule.lower()
        # Dict lookup is preferred over if/elif: adding new rules is one line.
        recurrence_deltas = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }
        delta = recurrence_deltas.get(rule)
        if delta is None:
            return None
        next_due = datetime.now() + delta

        return Task(
            name=self.name,
            task_type=self.task_type,
            priority=self.priority,
            duration_minutes=self.duration_minutes,
            pet_id=self.pet_id,
            preferred_window=self.preferred_window,
            is_recurring=self.is_recurring,
            recurrence_rule=self.recurrence_rule,
            due_datetime=next_due,
            notes=f"Auto-generated from recurring task (rule: {self.recurrence_rule})",
        )

    def mark_skipped(self, reason: str) -> None:
        """Set status to SKIPPED and record reason in notes."""
        self.status = TaskStatus.SKIPPED
        self.notes = f"Skipped: {reason}"

    def is_overdue(self) -> bool:
        """Return True if due_datetime has passed and task is not complete."""
        if self.due_datetime is None:
            return False
        return datetime.now() > self.due_datetime and self.status != TaskStatus.COMPLETED

    def get_urgency_score(self) -> float:
        """Return a numeric score combining priority, overdue status, and due time.

        Higher score = schedule sooner.
        Base score comes from priority value (1–4).
        Overdue tasks get a +10 bonus.
        Tasks due within 2 hours get a +2 bonus.
        """
        score = float(self.priority.value)
        if self.is_overdue():
            score += 10.0
        if self.due_datetime:
            minutes_until_due = (self.due_datetime - datetime.now()).total_seconds() / 60
            if 0 < minutes_until_due <= 120:
                score += 2.0
        return score


# ---------------------------------------------------------------------------
# ScheduledTask
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    task: Task
    start_time: datetime
    end_time: datetime
    reasoning: str = ""
    is_conflict: bool = False
    scheduled_task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_duration(self) -> int:
        """Return duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() // 60)

    def conflicts_with(self, other: ScheduledTask) -> bool:
        """Return True if this scheduled task overlaps with another."""
        return self.start_time < other.end_time and self.end_time > other.start_time


# ---------------------------------------------------------------------------
# DailySchedule
# ---------------------------------------------------------------------------

@dataclass
class DailySchedule:
    owner_id: str
    schedule_date: date
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)
    total_time_used_minutes: int = 0
    summary: str = ""

    def add_scheduled_task(self, st: ScheduledTask) -> None:
        """Append a ScheduledTask and update total time used."""
        self.scheduled_tasks.append(st)
        self.total_time_used_minutes += st.get_duration()

    def add_unscheduled_task(self, t: Task) -> None:
        """Append a Task to the unscheduled list."""
        self.unscheduled_tasks.append(t)

    def get_schedule_by_pet(self, pet_id: str) -> list[ScheduledTask]:
        """Return only the scheduled tasks belonging to a specific pet."""
        return [st for st in self.scheduled_tasks if st.task.pet_id == pet_id]

    def get_completion_rate(self) -> float:
        """Return fraction of tasks marked COMPLETED vs total scheduled."""
        if not self.scheduled_tasks:
            return 0.0
        completed = sum(1 for st in self.scheduled_tasks if st.task.status == TaskStatus.COMPLETED)
        return completed / len(self.scheduled_tasks)

    def sort_by_time(self) -> list[ScheduledTask]:
        """Return scheduled tasks sorted by start time (earliest first).

        Uses a lambda key so Python's sorted() compares datetime objects
        directly — no string parsing needed.
        """
        return sorted(self.scheduled_tasks, key=lambda st: st.start_time)

    def sort_by_priority(self) -> list[ScheduledTask]:
        """Return scheduled tasks sorted by priority (highest first).

        Priority enum values: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1.
        reverse=True puts the highest value first.
        """
        return sorted(self.scheduled_tasks, key=lambda st: st.task.priority.value, reverse=True)

    def filter_by_status(self, status: TaskStatus) -> list[ScheduledTask]:
        """Return only scheduled tasks whose underlying task matches the given status.

        Useful for separating completed tasks from still-pending ones after the
        owner has been checking off items throughout the day.

        Args:
            status: A TaskStatus enum value (e.g. TaskStatus.COMPLETED,
                    TaskStatus.SCHEDULED, TaskStatus.SKIPPED).

        Returns:
            A new list of ScheduledTask objects whose task.status == status.
            Returns an empty list if no tasks match.

        Example:
            done = schedule.filter_by_status(TaskStatus.COMPLETED)
        """
        return [st for st in self.scheduled_tasks if st.task.status == status]

    def filter_by_pet(self, pet_id: str) -> list[ScheduledTask]:
        """Return only scheduled tasks belonging to a specific pet.

        Allows an owner with multiple pets to view one animal's plan in isolation
        without regenerating the full schedule.

        Args:
            pet_id: The UUID string of the pet to filter by (Pet.pet_id).

        Returns:
            A new list of ScheduledTask objects whose task.pet_id matches pet_id.
            Returns an empty list if the pet has no scheduled tasks today.

        Example:
            mochi_tasks = schedule.filter_by_pet(mochi.pet_id)
        """
        return [st for st in self.scheduled_tasks if st.task.pet_id == pet_id]

    def to_dict(self) -> dict:
        """Serialize the schedule to a plain dict (for display / export)."""
        return {
            "schedule_id": self.schedule_id,
            "owner_id": self.owner_id,
            "date": str(self.schedule_date),
            "total_time_used_minutes": self.total_time_used_minutes,
            "summary": self.summary,
            "scheduled_tasks": [
                {
                    "task": st.task.name,
                    "type": st.task.task_type.value,
                    "priority": st.task.priority.name,
                    "start": st.start_time.strftime("%H:%M"),
                    "end": st.end_time.strftime("%H:%M"),
                    "duration_minutes": st.get_duration(),
                    "reasoning": st.reasoning,
                }
                for st in self.scheduled_tasks
            ],
            "unscheduled_tasks": [
                {
                    "task": t.name,
                    "type": t.task_type.value,
                    "priority": t.priority.name,
                    "reason": t.notes,
                }
                for t in self.unscheduled_tasks
            ],
        }


# ---------------------------------------------------------------------------
# SchedulerConfig
# ---------------------------------------------------------------------------

@dataclass
class SchedulerConfig:
    day_start_hour: int = 7
    day_end_hour: int = 21
    buffer_minutes_between_tasks: int = 10
    respect_preferred_windows: bool = True
    allow_task_splitting: bool = False
    optimization_strategy: str = "priority"   # "priority" | "time" | "balanced"


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str
    owner_id: str
    pet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    breed: str = ""
    age_years: int = 0
    weight_kg: float = 0.0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def update_profile(self, **kwargs) -> None:
        """Update any profile attribute by keyword argument."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks with PENDING status."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return tasks filtered by TaskType."""
        return [t for t in self.tasks if t.task_type == task_type]


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    owner_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    available_minutes_per_day: int = 120
    preferences: list[TimeWindow] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Append a pet to the owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by ID."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def update_profile(self, **kwargs) -> None:
        """Update any profile attribute by keyword argument."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_schedule(self, schedule_date: date) -> DailySchedule:
        """Convenience method — delegates to Scheduler."""
        scheduler = Scheduler(owner=self)
        return scheduler.generate_daily_schedule(schedule_date)


# ---------------------------------------------------------------------------
# TaskRepository
# ---------------------------------------------------------------------------

class TaskRepository:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Store a task by its ID."""
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, updates: dict) -> None:
        """Apply a dict of attribute updates to a stored task."""
        task = self.tasks.get(task_id)
        if task:
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def delete_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        self.tasks.pop(task_id, None)

    def get_tasks_for_pet(self, pet_id: str) -> list[Task]:
        """Return all tasks associated with a given pet."""
        return [t for t in self.tasks.values() if t.pet_id == pet_id]

    def get_overdue_tasks(self, pet_id: str) -> list[Task]:
        """Return overdue tasks for a given pet."""
        return [t for t in self.get_tasks_for_pet(pet_id) if t.is_overdue()]


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class NotificationService:
    def __init__(self) -> None:
        self.notification_log: list[str] = []

    def send_reminder(self, scheduled_task: ScheduledTask) -> None:
        """Log a reminder for an upcoming scheduled task."""
        msg = (
            f"REMINDER: '{scheduled_task.task.name}' starts at "
            f"{scheduled_task.start_time.strftime('%H:%M')}"
        )
        self.notification_log.append(msg)

    def send_daily_summary(self, schedule: DailySchedule) -> None:
        """Log a daily summary message."""
        msg = (
            f"DAILY SUMMARY ({schedule.schedule_date}): "
            f"{len(schedule.scheduled_tasks)} tasks scheduled, "
            f"{len(schedule.unscheduled_tasks)} unscheduled. "
            f"{schedule.total_time_used_minutes} min total."
        )
        self.notification_log.append(msg)

    def alert_overdue(self, task: Task) -> None:
        """Log an overdue alert for a task."""
        self.notification_log.append(f"OVERDUE: '{task.name}' is past due!")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(
        self,
        owner: Owner,
        config: Optional[SchedulerConfig] = None,
        repository: Optional[TaskRepository] = None,
        notifications: Optional[NotificationService] = None,
    ) -> None:
        self.scheduler_id: str = str(uuid.uuid4())
        self.owner: Owner = owner
        self.config: SchedulerConfig = config or SchedulerConfig()
        self.pets: list[Pet] = owner.pets
        self.repository: Optional[TaskRepository] = repository
        self.notifications: Optional[NotificationService] = notifications

    def generate_daily_schedule(self, schedule_date: date) -> DailySchedule:
        """Build and return a DailySchedule for the given date."""
        schedule = DailySchedule(
            owner_id=self.owner.owner_id,
            schedule_date=schedule_date,
        )

        # Collect all pending tasks across all pets
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_pending_tasks())

        # Sort by urgency
        prioritized = self.prioritize_tasks(all_tasks)

        # Assign to time slots
        scheduled = self.fit_tasks_to_window(prioritized, self.owner.available_minutes_per_day)

        for st in scheduled:
            st.task.status = TaskStatus.SCHEDULED
            schedule.add_scheduled_task(st)

        # Anything that didn't get scheduled
        scheduled_ids = {st.task.task_id for st in scheduled}
        for task in prioritized:
            if task.task_id not in scheduled_ids:
                task.mark_skipped("Not enough time in the day")
                schedule.add_unscheduled_task(task)

        schedule.summary = self.explain_plan(schedule)

        if self.notifications:
            self.notifications.send_daily_summary(schedule)

        return schedule

    def prioritize_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by urgency score (highest first)."""
        return sorted(tasks, key=lambda t: t.get_urgency_score(), reverse=True)

    def fit_tasks_to_window(
        self, tasks: list[Task], available_minutes: int
    ) -> list[ScheduledTask]:
        """Greedily assign tasks to time slots within the available window."""
        scheduled: list[ScheduledTask] = []
        minutes_remaining = available_minutes
        current_time = datetime.combine(
            date.today(),
            time(self.config.day_start_hour, 0)
        )
        buffer = self.config.buffer_minutes_between_tasks

        for task in tasks:
            total_needed = task.duration_minutes + (buffer if scheduled else 0)
            if total_needed > minutes_remaining:
                continue

            # Add buffer gap after the previous task
            if scheduled:
                current_time += timedelta(minutes=buffer)
                minutes_remaining -= buffer

            start = current_time
            end = start + timedelta(minutes=task.duration_minutes)

            # Don't schedule past the end of the day
            day_end = datetime.combine(date.today(), time(self.config.day_end_hour, 0))
            if end > day_end:
                continue

            reasoning = self._build_reasoning(task, minutes_remaining)
            scheduled.append(ScheduledTask(task=task, start_time=start, end_time=end, reasoning=reasoning))

            current_time = end
            minutes_remaining -= task.duration_minutes

        return scheduled

    def check_conflicts(self, schedule: DailySchedule) -> list[ScheduledTask]:
        """Detect and return all ScheduledTasks whose time windows overlap.

        Uses an O(n²) pairwise comparison — acceptable for the small task lists
        typical of a daily pet care schedule (usually fewer than 20 tasks).
        Each conflicting task is also flagged with is_conflict=True so the UI
        can highlight it without re-running this method.

        This method does not raise exceptions or modify the schedule structure;
        it only annotates tasks and returns the conflicting subset, so callers
        can display a warning rather than crashing.

        Args:
            schedule: The DailySchedule to inspect.

        Returns:
            A deduplicated list of ScheduledTask objects involved in at least
            one overlap. Returns an empty list if the schedule is conflict-free.

        Example:
            conflicts = scheduler.check_conflicts(schedule)
            if conflicts:
                print(f"{len(conflicts)} tasks have time conflicts.")
        """
        conflicts: list[ScheduledTask] = []
        tasks = schedule.scheduled_tasks
        for i, a in enumerate(tasks):
            for b in tasks[i + 1:]:
                if a.conflicts_with(b):
                    a.is_conflict = True
                    b.is_conflict = True
                    if a not in conflicts:
                        conflicts.append(a)
                    if b not in conflicts:
                        conflicts.append(b)
        return conflicts

    def explain_plan(self, schedule: DailySchedule) -> str:
        """Return a human-readable explanation of why the plan was built this way."""
        lines = [
            f"Plan for {schedule.schedule_date} - "
            f"{len(schedule.scheduled_tasks)} tasks scheduled, "
            f"{schedule.total_time_used_minutes} min used of "
            f"{self.owner.available_minutes_per_day} available.\n"
        ]
        for st in schedule.scheduled_tasks:
            lines.append(
                f"  {st.start_time.strftime('%H:%M')}-{st.end_time.strftime('%H:%M')}  "
                f"{st.task.name} [{st.task.priority.name}] - {st.reasoning}"
            )
        if schedule.unscheduled_tasks:
            lines.append("\nNot scheduled (insufficient time):")
            for t in schedule.unscheduled_tasks:
                lines.append(f"  - {t.name} [{t.priority.name}]")
        return "\n".join(lines)

    # --- Private helpers ---

    def _score_task(self, task: Task) -> float:
        """Compute a numeric score for a task used during prioritization."""
        return task.get_urgency_score()

    def _apply_time_constraints(self, task: Task) -> bool:
        """Return True if the task can fit within the owner's available time."""
        return task.duration_minutes <= self.owner.available_minutes_per_day

    def _calculate_available_slots(self) -> list[TimeWindow]:
        """Derive free time windows from owner preferences and config."""
        if self.owner.preferences:
            return [w for w in self.owner.preferences if w.is_active]
        # Fall back to a single window spanning the full config day
        return [
            TimeWindow(
                label="Full day",
                start_time=time(self.config.day_start_hour, 0),
                end_time=time(self.config.day_end_hour, 0),
            )
        ]

    def _build_reasoning(self, task: Task, minutes_remaining: int) -> str:
        """Build a short explanation string for why a task was placed."""
        return (
            f"Priority {task.priority.name.lower()}, "
            f"{task.duration_minutes} min, "
            f"{minutes_remaining} min remaining in day"
        )
