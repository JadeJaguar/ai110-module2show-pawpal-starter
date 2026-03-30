"""
PawPal+ — Backend Logic Layer
All core classes live here: enums, data models, scheduler, and supporting services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
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
        pass

    def duration_minutes(self) -> int:
        """Return the length of this window in minutes."""
        pass

    def overlaps(self, other: TimeWindow) -> bool:
        """Return True if this window overlaps with another."""
        pass


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
        pass

    def mark_skipped(self, reason: str) -> None:
        """Set status to SKIPPED and record reason in notes."""
        pass

    def is_overdue(self) -> bool:
        """Return True if due_datetime has passed and task is not complete."""
        pass

    def get_urgency_score(self) -> float:
        """Return a numeric score combining priority, overdue status, and due time."""
        pass


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
        pass

    def conflicts_with(self, other: ScheduledTask) -> bool:
        """Return True if this scheduled task overlaps with another."""
        pass


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
        pass

    def add_unscheduled_task(self, t: Task) -> None:
        """Append a Task to the unscheduled list."""
        pass

    def get_schedule_by_pet(self, pet_id: str) -> list[ScheduledTask]:
        """Return only the scheduled tasks belonging to a specific pet."""
        pass

    def get_completion_rate(self) -> float:
        """Return fraction of tasks marked COMPLETED vs total scheduled."""
        pass

    def to_dict(self) -> dict:
        """Serialize the schedule to a plain dict (for display / export)."""
        pass


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
        pass

    def remove_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        pass

    def update_profile(self, **kwargs) -> None:
        """Update any profile attribute by keyword argument."""
        pass

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks with PENDING status."""
        pass

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return tasks filtered by TaskType."""
        pass


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
        pass

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by ID."""
        pass

    def update_profile(self, **kwargs) -> None:
        """Update any profile attribute by keyword argument."""
        pass

    def get_schedule(self, schedule_date: date) -> DailySchedule:
        """Convenience method — delegates to Scheduler."""
        pass


# ---------------------------------------------------------------------------
# TaskRepository
# ---------------------------------------------------------------------------

class TaskRepository:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Store a task by its ID."""
        pass

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        pass

    def update_task(self, task_id: str, updates: dict) -> None:
        """Apply a dict of attribute updates to a stored task."""
        pass

    def delete_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        pass

    def get_tasks_for_pet(self, pet_id: str) -> list[Task]:
        """Return all tasks associated with a given pet."""
        pass

    def get_overdue_tasks(self, pet_id: str) -> list[Task]:
        """Return overdue tasks for a given pet."""
        pass


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class NotificationService:
    def __init__(self) -> None:
        self.notification_log: list[str] = []

    def send_reminder(self, scheduled_task: ScheduledTask) -> None:
        """Log a reminder for an upcoming scheduled task."""
        pass

    def send_daily_summary(self, schedule: DailySchedule) -> None:
        """Log a daily summary message."""
        pass

    def alert_overdue(self, task: Task) -> None:
        """Log an overdue alert for a task."""
        pass


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
        pass

    def prioritize_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by urgency score (highest first)."""
        pass

    def fit_tasks_to_window(
        self, tasks: list[Task], available_minutes: int
    ) -> list[ScheduledTask]:
        """Greedily assign tasks to time slots within the available window."""
        pass

    def check_conflicts(self, schedule: DailySchedule) -> list[ScheduledTask]:
        """Return any ScheduledTasks that overlap in time."""
        pass

    def explain_plan(self, schedule: DailySchedule) -> str:
        """Return a human-readable explanation of why the plan was built this way."""
        pass

    # --- Private helpers ---

    def _score_task(self, task: Task) -> float:
        """Compute a numeric score for a task used during prioritization."""
        pass

    def _apply_time_constraints(self, task: Task) -> bool:
        """Return True if the task can fit within the owner's available time."""
        pass

    def _calculate_available_slots(self) -> list[TimeWindow]:
        """Derive free time windows from owner preferences and config."""
        pass
