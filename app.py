import streamlit as st
from datetime import date, datetime, time, timedelta
from pawpal_system import (
    Owner, Pet, Task, Scheduler, SchedulerConfig,
    TaskType, Priority, TaskStatus, TimeWindow,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "owners" not in st.session_state:
    st.session_state.owners = []

if "active_owner_id" not in st.session_state:
    st.session_state.active_owner_id = None

if "schedules" not in st.session_state:
    st.session_state.schedules = {}

if "schedulers" not in st.session_state:
    st.session_state.schedulers = {}


def get_active_owner() -> Owner | None:
    if st.session_state.active_owner_id is None:
        return None
    return next(
        (o for o in st.session_state.owners if o.owner_id == st.session_state.active_owner_id),
        None,
    )


def _remove_owner_callback() -> None:
    """Runs BEFORE the script reruns, so active_owner_select can be safely updated."""
    selected = st.session_state.get("active_owner_select")
    to_remove = next((o for o in st.session_state.owners if o.name == selected), None)
    if not to_remove:
        return
    st.session_state.owners.remove(to_remove)
    st.session_state.schedules.pop(to_remove.owner_id, None)
    st.session_state.schedulers.pop(to_remove.owner_id, None)
    if st.session_state.owners:
        first = st.session_state.owners[0]
        st.session_state.active_owner_id = first.owner_id
        st.session_state["active_owner_select"] = first.name
    else:
        st.session_state.active_owner_id = None
        st.session_state.pop("active_owner_select", None)


# ---------------------------------------------------------------------------
# Section 1: Owner & Pet info
# ---------------------------------------------------------------------------
st.subheader("Owner & Pet Info")

# 1a. Add owner & pet form — always first, expanded until first owner exists
with st.expander("Add owner & pet", expanded=not st.session_state.owners):
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
        existing = next((o for o in st.session_state.owners if o.name == owner_name), None)
        if existing is None:
            existing = Owner(name=owner_name, available_minutes_per_day=available_minutes)
            st.session_state.owners.append(existing)
        else:
            existing.available_minutes_per_day = available_minutes

        # Sync active owner — set BEFORE the selectbox renders below
        st.session_state.active_owner_id = existing.owner_id
        st.session_state["active_owner_select"] = existing.name

        pet = Pet(name=pet_name, species=species, owner_id=existing.owner_id)
        existing.add_pet(pet)
        st.session_state.schedules.pop(existing.owner_id, None)
        st.success(f"Added {pet_name} ({species}) to {existing.name}'s profile")

# 1b. Active owner selector — appears after the form, once owners exist
if st.session_state.owners:
    owner_labels = [o.name for o in st.session_state.owners]

    col_sel, col_del = st.columns([5, 1])
    with col_sel:
        # key="active_owner_select" lets us pre-set the value via session state
        selected_name = st.selectbox(
            "Active owner",
            owner_labels,
            key="active_owner_select",
        )
    with col_del:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        st.button("Remove", key="remove_owner", type="secondary", on_click=_remove_owner_callback)

    # Keep active_owner_id in sync with whatever the selectbox shows
    st.session_state.active_owner_id = next(
        (o.owner_id for o in st.session_state.owners if o.name == selected_name), None
    )

active_owner = get_active_owner()

# 1c. Registered pets + remove pet
if active_owner and active_owner.pets:
    st.markdown(f"**{active_owner.name}'s registered pets:**")
    st.table([
        {"Name": p.name, "Species": p.species, "Tasks added": len(p.tasks)}
        for p in active_owner.pets
    ])

    col_psel, col_pdel = st.columns([5, 1])
    with col_psel:
        pet_to_remove_name = st.selectbox(
            "Remove pet",
            [p.name for p in active_owner.pets],
            key="pet_remove_select",
            label_visibility="collapsed",
        )
    with col_pdel:
        if st.button("Remove", key="remove_pet", type="secondary"):
            pet_to_remove = next(
                (p for p in active_owner.pets if p.name == pet_to_remove_name), None
            )
            if pet_to_remove:
                active_owner.remove_pet(pet_to_remove.pet_id)
                st.session_state.schedules.pop(active_owner.owner_id, None)
                st.rerun()

# ---------------------------------------------------------------------------
# Section 2: Add tasks
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Add Tasks")

if active_owner is None or not active_owner.pets:
    st.info("Save an owner & pet above before adding tasks.")
else:
    pet_options = {f"{p.name} ({p.species})": p for p in active_owner.pets}
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

    want_pref_time = st.checkbox("Set a preferred time for this task")
    pref_time = None
    if want_pref_time:
        pref_time = st.time_input("Preferred start time", value=time(8, 0), step=300)

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
        st.session_state.schedules.pop(active_owner.owner_id, None)
        pref_label = f" at {pref_time.strftime('%H:%M')}" if pref_time else ""
        rec_label = f" ({recurrence_rule})" if recurrence_rule else ""
        st.success(f"Added: {task_name} ({priority}){pref_label}{rec_label} → {selected_pet.name}")

    # Current tasks table
    all_tasks_meta = []  # (label, task_id, pet_id) for remove selectbox
    display_rows = []
    for p in active_owner.pets:
        for t in p.tasks:
            all_tasks_meta.append((f"{p.name}: {t.name}", t.task_id, p.pet_id))
            display_rows.append({
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

    if display_rows:
        st.markdown("**Current tasks:**")
        st.table(display_rows)

        # Remove task
        task_labels = [m[0] for m in all_tasks_meta]
        col_tsel, col_tdel = st.columns([5, 1])
        with col_tsel:
            task_to_remove_label = st.selectbox(
                "Remove task",
                task_labels,
                key="task_remove_select",
                label_visibility="collapsed",
            )
        with col_tdel:
            if st.button("Remove", key="remove_task", type="secondary"):
                match = next((m for m in all_tasks_meta if m[0] == task_to_remove_label), None)
                if match:
                    _, task_id, pet_id = match
                    pet = next((p for p in active_owner.pets if p.pet_id == pet_id), None)
                    if pet:
                        pet.remove_task(task_id)
                        st.session_state.schedules.pop(active_owner.owner_id, None)
                        st.rerun()
    else:
        st.info("No tasks yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 3: Generate schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Generate Daily Schedule")

has_tasks = active_owner is not None and any(p.tasks for p in active_owner.pets)

if active_owner is None:
    st.info("Complete owner & pet setup above first.")
elif not has_tasks:
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule"):
        for pet in active_owner.pets:
            for task in pet.tasks:
                if task.status in (TaskStatus.SCHEDULED, TaskStatus.SKIPPED):
                    task.status = TaskStatus.PENDING

        config = SchedulerConfig(optimization_strategy="priority")
        scheduler = Scheduler(owner=active_owner, config=config)
        schedule = scheduler.generate_daily_schedule(date.today())
        st.session_state.schedules[active_owner.owner_id] = schedule
        st.session_state.schedulers[active_owner.owner_id] = scheduler

    schedule = st.session_state.schedules.get(active_owner.owner_id)
    scheduler = st.session_state.schedulers.get(active_owner.owner_id) or Scheduler(owner=active_owner)

    if schedule:
        total_available = active_owner.available_minutes_per_day
        time_used = schedule.total_time_used_minutes

        m1, m2 = st.columns(2)
        m1.metric("Time used", f"{time_used} min", delta=f"{total_available - time_used} min free")
        m2.metric("Tasks scheduled", len(schedule.scheduled_tasks))

        # Conflict detection — live on every render
        conflicts = scheduler.check_conflicts(schedule)
        if conflicts:
            seen = set()
            conflict_lines = []
            for c in conflicts:
                for other in conflicts:
                    if c.scheduled_task_id == other.scheduled_task_id:
                        continue
                    pair = tuple(sorted([c.scheduled_task_id, other.scheduled_task_id]))
                    if pair not in seen and c.conflicts_with(other):
                        seen.add(pair)
                        overlap_minutes = int(
                            (min(c.end_time, other.end_time) - max(c.start_time, other.start_time))
                            .total_seconds() / 60
                        )
                        fix_time = other.end_time.strftime("%H:%M")
                        conflict_lines.append(
                            f"- **{c.task.name}** "
                            f"({c.start_time.strftime('%H:%M')}–{c.end_time.strftime('%H:%M')}) "
                            f"overlaps **{other.task.name}** "
                            f"({other.start_time.strftime('%H:%M')}–{other.end_time.strftime('%H:%M')}) "
                            f"by {overlap_minutes} min — move one to start at **{fix_time}** or later"
                        )
            st.warning(
                f"**{len(seen)} conflict(s) detected** — use the time inputs below to resolve:\n\n"
                + "\n\n".join(conflict_lines)
            )
        else:
            st.success(
                f"Schedule for {schedule.schedule_date} — "
                f"{time_used} / {total_available} min used — no conflicts"
            )

        # Sort + filter controls
        if schedule.scheduled_tasks:
            ctrl1, ctrl2 = st.columns([2, 2])
            with ctrl1:
                sort_mode = st.radio(
                    "Sort by",
                    ["Time (earliest first)", "Priority (highest first)"],
                    horizontal=True,
                )
            with ctrl2:
                pet_filter_options = ["All pets"] + [p.name for p in active_owner.pets]
                pet_filter = st.selectbox("Filter by pet", pet_filter_options)

            if sort_mode == "Time (earliest first)":
                display_tasks = schedule.sort_by_time()
            else:
                display_tasks = schedule.sort_by_priority()

            if pet_filter != "All pets":
                target_pet_id = next(
                    (p.pet_id for p in active_owner.pets if p.name == pet_filter), None
                )
                if target_pet_id:
                    display_tasks = [s for s in display_tasks if s.task.pet_id == target_pet_id]

        # Scheduled tasks list
        if schedule.scheduled_tasks:
            st.markdown("#### Scheduled Tasks")
            st.caption("Check a task to mark it complete. Use the time input to override the generated start time.")

            for s in display_tasks:
                col_check, col_info, col_time = st.columns([1, 6, 2])

                with col_check:
                    done = st.checkbox(
                        "Mark complete",
                        value=(s.task.status == TaskStatus.COMPLETED),
                        key=f"done_{s.scheduled_task_id}",
                        label_visibility="collapsed",
                    )
                    if done and s.task.status != TaskStatus.COMPLETED:
                        s.task.mark_complete()
                        next_task = s.task.generate_next_occurrence()
                        if next_task:
                            for pet in active_owner.pets:
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

            # Progress bar AFTER the loop — reflects mark_complete() calls from this render
            completion_rate = schedule.get_completion_rate()
            st.divider()
            st.progress(
                completion_rate,
                text=f"Day progress — {int(completion_rate * 100)}% complete",
            )

        if schedule.unscheduled_tasks:
            st.markdown("#### Could Not Schedule")
            st.table([
                {"Task": t.name, "Priority": t.priority.name, "Reason": t.notes}
                for t in schedule.unscheduled_tasks
            ])

        with st.expander("Plan summary (reasoning)"):
            st.text(schedule.summary)
