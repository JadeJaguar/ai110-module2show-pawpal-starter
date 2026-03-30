"""
tests/test_pawpal.py — Core behavior tests for PawPal+
Run: python -m pytest
"""

from pawpal_system import Owner, Pet, Task, TaskType, Priority, TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pet(owner_id: str = "owner-1") -> Pet:
    return Pet(name="Mochi", species="dog", owner_id=owner_id)


def make_task(pet_id: str = "pet-1") -> Task:
    return Task(
        name="Morning walk",
        task_type=TaskType.WALK,
        priority=Priority.HIGH,
        duration_minutes=30,
        pet_id=pet_id,
    )


# ---------------------------------------------------------------------------
# Test 1: mark_complete() changes task status to COMPLETED
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = make_task()
    assert task.status == TaskStatus.PENDING
    task.mark_complete()
    assert task.status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# Test 2: add_task() increases the pet's task count
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    pet = make_pet()
    assert len(pet.tasks) == 0
    pet.add_task(make_task(pet_id=pet.pet_id))
    assert len(pet.tasks) == 1
    pet.add_task(make_task(pet_id=pet.pet_id))
    assert len(pet.tasks) == 2
