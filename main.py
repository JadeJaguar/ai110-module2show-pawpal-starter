"""
main.py — PawPal+ demo script (CLI-first workflow)
Run: python main.py
"""

from datetime import date
from pawpal_system import (
    Owner, Pet, Task, Scheduler, SchedulerConfig,
    TaskType, Priority,
)

# ---------------------------------------------------------------------------
# Setup: Owner
# ---------------------------------------------------------------------------
jordan = Owner(
    name="Jordan",
    email="jordan@example.com",
    available_minutes_per_day=120,
)

# ---------------------------------------------------------------------------
# Setup: Pets
# ---------------------------------------------------------------------------
mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3, owner_id=jordan.owner_id)
luna  = Pet(name="Luna",  species="cat", breed="Tabby",     age_years=5, owner_id=jordan.owner_id)

# ---------------------------------------------------------------------------
# Setup: Tasks for Mochi
# ---------------------------------------------------------------------------
mochi.add_task(Task(
    name="Morning walk",
    task_type=TaskType.WALK,
    priority=Priority.HIGH,
    duration_minutes=30,
    pet_id=mochi.pet_id,
))

mochi.add_task(Task(
    name="Heartworm medication",
    task_type=TaskType.MEDICATION,
    priority=Priority.CRITICAL,
    duration_minutes=5,
    pet_id=mochi.pet_id,
))

mochi.add_task(Task(
    name="Obedience training",
    task_type=TaskType.TRAINING,
    priority=Priority.MEDIUM,
    duration_minutes=20,
    pet_id=mochi.pet_id,
))

# ---------------------------------------------------------------------------
# Setup: Tasks for Luna
# ---------------------------------------------------------------------------
luna.add_task(Task(
    name="Breakfast feeding",
    task_type=TaskType.FEEDING,
    priority=Priority.HIGH,
    duration_minutes=10,
    pet_id=luna.pet_id,
))

luna.add_task(Task(
    name="Brush coat",
    task_type=TaskType.GROOMING,
    priority=Priority.LOW,
    duration_minutes=15,
    pet_id=luna.pet_id,
))

# ---------------------------------------------------------------------------
# Register pets with owner
# ---------------------------------------------------------------------------
jordan.add_pet(mochi)
jordan.add_pet(luna)

# ---------------------------------------------------------------------------
# Run scheduler
# ---------------------------------------------------------------------------
config = SchedulerConfig(
    day_start_hour=7,
    day_end_hour=21,
    buffer_minutes_between_tasks=10,
    optimization_strategy="priority",
)

scheduler = Scheduler(owner=jordan, config=config)
schedule  = scheduler.generate_daily_schedule(date.today())

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------
print("=" * 55)
print("        PAWPAL+ - TODAY'S SCHEDULE")
print("=" * 55)
print(f"  Owner : {jordan.name}")
print(f"  Date  : {schedule.schedule_date}")
print(f"  Time  : {schedule.total_time_used_minutes} / {jordan.available_minutes_per_day} min used")
print("=" * 55)

print("\n SCHEDULED TASKS")
print("-" * 55)
for st in schedule.scheduled_tasks:
    print(
        f"  {st.start_time.strftime('%H:%M')} - {st.end_time.strftime('%H:%M')}"
        f"  {st.task.name} ({st.task.task_type.value})"
        f"  [{st.task.priority.name}]"
    )
    print(f"           -> {st.reasoning}")

if schedule.unscheduled_tasks:
    print("\n UNSCHEDULED TASKS (didn't fit)")
    print("-" * 55)
    for t in schedule.unscheduled_tasks:
        print(f"  - {t.name} [{t.priority.name}]  {t.notes}")

print("\n SUMMARY")
print("-" * 55)
print(schedule.summary)
print("=" * 55)
