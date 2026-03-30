"""
main.py — PawPal+ demo script (CLI-first workflow)
Run: python main.py
"""

from datetime import date, datetime, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler, SchedulerConfig,
    TaskType, Priority, TaskStatus, DailySchedule, ScheduledTask,
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
# Setup: Tasks added intentionally OUT OF PRIORITY ORDER
# (low → medium → high → critical) to prove sorting works
# ---------------------------------------------------------------------------
mochi.add_task(Task(
    name="Brush coat",
    task_type=TaskType.GROOMING,
    priority=Priority.LOW,
    duration_minutes=15,
    pet_id=mochi.pet_id,
))

mochi.add_task(Task(
    name="Obedience training",
    task_type=TaskType.TRAINING,
    priority=Priority.MEDIUM,
    duration_minutes=20,
    pet_id=mochi.pet_id,
))

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
    is_recurring=True,
    recurrence_rule="daily",
))

luna.add_task(Task(
    name="Breakfast feeding",
    task_type=TaskType.FEEDING,
    priority=Priority.HIGH,
    duration_minutes=10,
    pet_id=luna.pet_id,
))

luna.add_task(Task(
    name="Flea treatment",
    task_type=TaskType.MEDICATION,
    priority=Priority.CRITICAL,
    duration_minutes=5,
    pet_id=luna.pet_id,
    is_recurring=True,
    recurrence_rule="weekly",
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
# Print: raw schedule (insertion order — unsorted)
# ---------------------------------------------------------------------------
print("=" * 55)
print("        PAWPAL+ - TODAY'S SCHEDULE")
print("=" * 55)
print(f"  Owner : {jordan.name}")
print(f"  Date  : {schedule.schedule_date}")
print(f"  Time  : {schedule.total_time_used_minutes} / {jordan.available_minutes_per_day} min used")
print("=" * 55)

# ---------------------------------------------------------------------------
# SORT BY TIME — earliest task first
# ---------------------------------------------------------------------------
print("\n SORTED BY START TIME")
print("-" * 55)
for st in schedule.sort_by_time():
    print(
        f"  {st.start_time.strftime('%H:%M')} - {st.end_time.strftime('%H:%M')}"
        f"  {st.task.name} [{st.task.priority.name}]"
    )

# ---------------------------------------------------------------------------
# SORT BY PRIORITY — most urgent first
# ---------------------------------------------------------------------------
print("\n SORTED BY PRIORITY (highest first)")
print("-" * 55)
for st in schedule.sort_by_priority():
    print(
        f"  [{st.task.priority.name:8}]  {st.task.name}"
        f"  ({st.start_time.strftime('%H:%M')})"
    )

# ---------------------------------------------------------------------------
# FILTER BY PET — tasks per animal
# ---------------------------------------------------------------------------
print("\n FILTER BY PET")
print("-" * 55)
for pet in jordan.pets:
    pet_tasks = schedule.filter_by_pet(pet.pet_id)
    print(f"  {pet.name} ({pet.species}) — {len(pet_tasks)} scheduled task(s):")
    for st in pet_tasks:
        print(f"    • {st.task.name} [{st.task.priority.name}]  {st.start_time.strftime('%H:%M')}")

# ---------------------------------------------------------------------------
# FILTER BY STATUS — scheduled vs skipped
# ---------------------------------------------------------------------------
print("\n FILTER BY STATUS")
print("-" * 55)
scheduled_tasks = schedule.filter_by_status(TaskStatus.SCHEDULED)
print(f"  SCHEDULED ({len(scheduled_tasks)}):")
for st in scheduled_tasks:
    print(f"    • {st.task.name}")

skipped_tasks = schedule.unscheduled_tasks  # these never made it in
print(f"\n  SKIPPED / DIDN'T FIT ({len(skipped_tasks)}):")
for t in skipped_tasks:
    print(f"    • {t.name} [{t.priority.name}]  {t.notes}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n SUMMARY")
print("-" * 55)
print(schedule.summary)
print("=" * 55)

# ---------------------------------------------------------------------------
# RECURRING TASKS DEMO
# Mark a recurring task complete → generate next occurrence
# ---------------------------------------------------------------------------
print("\n RECURRING TASK DEMO")
print("-" * 55)

recurring_demo_tasks = [
    st for st in schedule.scheduled_tasks if st.task.is_recurring
]

for st in recurring_demo_tasks:
    task = st.task
    print(f"  Completing: '{task.name}' (rule: {task.recurrence_rule})")
    task.mark_complete()

    next_task = task.generate_next_occurrence()
    if next_task:
        print(f"  > Next occurrence created:")
        print(f"      Name     : {next_task.name}")
        print(f"      Rule     : {next_task.recurrence_rule}")
        print(f"      Due      : {next_task.due_datetime.strftime('%Y-%m-%d %H:%M')}")
        print(f"      Status   : {next_task.status.value}")
        print(f"      Note     : {next_task.notes}")
    print()

print("=" * 55)

# ---------------------------------------------------------------------------
# CONFLICT DETECTION DEMO
# The greedy scheduler never overlaps tasks by design, so we manually build
# a small DailySchedule with two overlapping ScheduledTasks to prove
# check_conflicts() catches them and returns warnings without crashing.
# ---------------------------------------------------------------------------
print("\n CONFLICT DETECTION DEMO")
print("-" * 55)

# Two tasks that overlap: walk 09:00-09:30, training 09:15-09:45 (15-min overlap)
base = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)

conflict_task_a = Task(
    name="Morning walk (manual)",
    task_type=TaskType.WALK,
    priority=Priority.HIGH,
    duration_minutes=30,
    pet_id=mochi.pet_id,
)
conflict_task_b = Task(
    name="Obedience training (manual)",
    task_type=TaskType.TRAINING,
    priority=Priority.MEDIUM,
    duration_minutes=30,
    pet_id=mochi.pet_id,
)

st_a = ScheduledTask(task=conflict_task_a, start_time=base,                        end_time=base + timedelta(minutes=30))
st_b = ScheduledTask(task=conflict_task_b, start_time=base + timedelta(minutes=15),
                     end_time=base + timedelta(minutes=45))

demo_schedule = DailySchedule(owner_id=jordan.owner_id, schedule_date=date.today())
demo_schedule.add_scheduled_task(st_a)
demo_schedule.add_scheduled_task(st_b)

conflicts = scheduler.check_conflicts(demo_schedule)

if conflicts:
    print(f"  WARNING: {len(conflicts)} conflicting task(s) detected:")
    for c in conflicts:
        print(
            f"    - '{c.task.name}'"
            f"  {c.start_time.strftime('%H:%M')}-{c.end_time.strftime('%H:%M')}"
            f"  [{c.task.priority.name}]"
        )
    print()
    print("  Tip: Adjust start times or reduce duration to resolve conflicts.")
else:
    print("  No conflicts detected.")

print("=" * 55)
