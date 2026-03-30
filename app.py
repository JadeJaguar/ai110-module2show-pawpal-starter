import streamlit as st
from datetime import date, datetime, time, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler, SchedulerConfig,
    TaskType, Priority, TaskStatus, TimeWindow,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state — initialize once, persist across reruns
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

if "schedule" not in st.session_state:
    st.session_state.schedule = None

# ---------------------------------------------------------------------------
# Section 1: Owner + Pet info
# ---------------------------------------------------------------------------
st.subheader("Owner & Pet Info")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input(
        "Available minutes today", min_value=30, max_value=480, value=120, step=10
    )
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Save owner & pet"):
    if st.session_state.owner is None:
        owner = Owner(name=owner_name, available_minutes_per_day=available_minutes)
        st.session_state.owner = owner
    else:
        st.session_state.owner.available_minutes_per_day = available_minutes

    pet = Pet(name=pet_name, species=species, owner_id=st.session_state.owner.owner_id)
    st.session_state.owner.add_pet(pet)
    st.session_state.schedule = None
    st.success(f"Added pet: {pet_name} ({species}) to {st.session_state.owner.name}'s profile")

if st.session_state.owner and st.session_state.owner.pets:
    st.markdown("**Registered pets:**")
    st.table([
        {"Name": p.name, "Species": p.species, "Tasks added": len(p.tasks)}
        for p in st.session_state.owner.pets
    ])

# ---------------------------------------------------------------------------
# Section 2: Add tasks
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Add Tasks")

if st.session_state.owner is None or not st.session_state.owner.pets:
    st.info("Save an owner & pet above before adding tasks.")
else:
    pet_options = {f"{p.name} ({p.species})": p for p in st.session_state.owner.pets}
    selected_pet_label = st.selectbox("Select pet", list(pet_options.keys()))
    selected_pet = pet_options[selected_pet_label]

    col1, col2, col3 = st.columns(3)
    with col1:
        task_name = st.text_input("Task name", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        task_type = st.selectbox("Type", [t.value for t in TaskType])

    priority = st.select_slider(
        "Priority", options=["LOW", "MEDIUM", "HIGH", "CRITICAL"], value="MEDIUM"
    )

    # Feature 3: optional preferred time
    want_pref_time = st.checkbox("Set a preferred time for this task")
    pref_time = None
    if want_pref_time:
        pref_time = st.time_input("Preferred start time", value=time(8, 0), step=300)

    # Recurring task options
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        is_recurring = st.checkbox("Recurring task")
    with col_rec2:
        recurrence_rule = None
        if is_recurring:
            recurrence_rule = st.selectbox("Repeats", ["daily", "weekly"])

    if st.button("Add task"):
        task = Task(
            name=task_name,
            task_type=TaskType(task_type),
            priority=Priority[priority],
            duration_minutes=int(duration),
            pet_id=selected_pet.pet_id,
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule,
        )
        if pref_time is not None:
            window_end = (
                datetime.combine(date.today(), pref_time) + timedelta(minutes=int(duration))
            ).time()
            task.preferred_window = TimeWindow(
                label="Preferred",
                start_time=pref_time,
                end_time=window_end,
            )
        selected_pet.add_task(task)
        st.session_state.schedule = None
        pref_label = f" at {pref_time.strftime('%H:%M')}" if pref_time else ""
        rec_label = f" ({recurrence_rule})" if recurrence_rule else ""
        st.success(f"Added: {task_name} ({priority}){pref_label}{rec_label} → {selected_pet.name}")

    # Show all tasks across all pets
    all_tasks = []
    for p in st.session_state.owner.pets:
        for t in p.tasks:
            all_tasks.append({
                "Pet": p.name,
                "Task": t.name,
                "Type": t.task_type.value,
                "Priority": t.priority.name,
                "Duration (min)": t.duration_minutes,
                "Preferred Time": (
                    t.preferred_window.start_time.strftime("%H:%M")
                    if t.preferred_window else "—"
                ),
                "Recurring": t.recurrence_rule if t.is_recurring else "—",
                "Status": t.status.value,
            })

    if all_tasks:
        st.markdown("**Current tasks:**")
        st.table(all_tasks)
    else:
        st.info("No tasks yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 3: Generate schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Generate Daily Schedule")

has_tasks = st.session_state.owner is not None and any(
    p.tasks for p in st.session_state.owner.pets
)

if st.session_state.owner is None:
    st.info("Complete owner & pet setup above first.")
elif not has_tasks:
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule"):
        for pet in st.session_state.owner.pets:
            for task in pet.tasks:
                if task.status in (TaskStatus.SCHEDULED, TaskStatus.SKIPPED):
                    task.status = TaskStatus.PENDING

        config = SchedulerConfig(optimization_strategy="priority")
        scheduler = Scheduler(owner=st.session_state.owner, config=config)
        st.session_state.schedule = scheduler.generate_daily_schedule(date.today())
        st.session_state.scheduler = scheduler

    if st.session_state.schedule:
        schedule = st.session_state.schedule
        scheduler = st.session_state.get("scheduler") or Scheduler(owner=st.session_state.owner)

        st.success(
            f"Schedule generated for {schedule.schedule_date} — "
            f"{schedule.total_time_used_minutes} / "
            f"{st.session_state.owner.available_minutes_per_day} min used"
        )

        # Conflict detection — runs after every render so time overrides are checked live
        conflicts = scheduler.check_conflicts(schedule)
        if conflicts:
            conflict_lines = []
            seen = set()
            for c in conflicts:
                for other in conflicts:
                    if c.scheduled_task_id != other.scheduled_task_id:
                        pair = tuple(sorted([c.scheduled_task_id, other.scheduled_task_id]))
                        if pair not in seen and c.conflicts_with(other):
                            seen.add(pair)
                            conflict_lines.append(
                                f"**{c.task.name}** ({c.start_time.strftime('%H:%M')}–{c.end_time.strftime('%H:%M')})"
                                f" overlaps with "
                                f"**{other.task.name}** ({other.start_time.strftime('%H:%M')}–{other.end_time.strftime('%H:%M')})"
                            )
            st.warning(
                "**Schedule conflicts detected** — adjust start times to resolve:\n\n"
                + "\n\n".join(f"- {line}" for line in conflict_lines)
            )

        # Scheduled tasks — checkboxes + time override
        if schedule.scheduled_tasks:
            st.markdown("#### Scheduled Tasks")
            st.caption("Check a task to mark it complete. Adjust the start time to override the generated schedule.")

            for s in schedule.scheduled_tasks:
                col_check, col_info, col_time = st.columns([1, 6, 2])

                # Feature 1: mark complete checkbox
                with col_check:
                    done = st.checkbox(
                        "Mark complete",
                        value=(s.task.status == TaskStatus.COMPLETED),
                        key=f"done_{s.scheduled_task_id}",
                        label_visibility="collapsed",
                    )
                    if done and s.task.status != TaskStatus.COMPLETED:
                        s.task.mark_complete()
                        # Recurring: auto-create next occurrence
                        next_task = s.task.generate_next_occurrence()
                        if next_task:
                            for pet in st.session_state.owner.pets:
                                if pet.pet_id == s.task.pet_id:
                                    pet.add_task(next_task)
                                    rule = s.task.recurrence_rule
                                    st.toast(
                                        f"'{s.task.name}' marked done — next {rule} instance queued.",
                                        icon="🔁",
                                    )
                                    break
                    elif not done and s.task.status == TaskStatus.COMPLETED:
                        s.task.status = TaskStatus.SCHEDULED

                # Task info
                with col_info:
                    if s.task.status == TaskStatus.COMPLETED:
                        name_display = f"~~{s.task.name}~~"
                    elif s.is_conflict:
                        name_display = f"**{s.task.name}** :warning:"
                    else:
                        name_display = f"**{s.task.name}**"
                    st.markdown(
                        f"{name_display} &nbsp; `{s.task.priority.name}` &nbsp; _{s.task.task_type.value}_  \n"
                        f"{s.start_time.strftime('%H:%M')} – {s.end_time.strftime('%H:%M')} &nbsp; · &nbsp; {s.reasoning}"
                    )

                # Feature 2: manual time override
                with col_time:
                    new_start = st.time_input(
                        "Override start time",
                        value=s.start_time.time(),
                        key=f"override_{s.scheduled_task_id}",
                        step=300,
                        label_visibility="collapsed",
                    )
                    if new_start != s.start_time.time():
                        new_dt = datetime.combine(schedule.schedule_date, new_start)
                        s.start_time = new_dt
                        s.end_time = new_dt + timedelta(minutes=s.task.duration_minutes)

        # Unscheduled tasks
        if schedule.unscheduled_tasks:
            st.markdown("#### Could Not Schedule")
            st.table([
                {
                    "Task": t.name,
                    "Priority": t.priority.name,
                    "Reason": t.notes,
                }
                for t in schedule.unscheduled_tasks
            ])

        # Summary
        st.markdown("#### Plan Summary")
        st.text(schedule.summary)
