classDiagram
    direction TB

    class Owner {
        +String owner_id
        +String name
        +String email
        +int available_minutes_per_day
        +List~TimeWindow~ preferences
        +List~Pet~ pets
        +add_pet(pet Pet) None
        +remove_pet(pet_id String) None
        +update_profile(kwargs) None
        +get_schedule(date date) DailySchedule
    }

    class Pet {
        +String pet_id
        +String name
        +String species
        +String breed
        +int age_years
        +float weight_kg
        +String owner_id
        +List~Task~ tasks
        +add_task(task Task) None
        +remove_task(task_id String) None
        +update_profile(kwargs) None
        +get_pending_tasks() List~Task~
        +get_tasks_by_type(task_type TaskType) List~Task~
    }

    class TimeWindow {
        +String label
        +time start_time
        +time end_time
        +List~str~ days_of_week
        +bool is_active
        +contains(dt datetime) bool
        +duration_minutes() int
        +overlaps(other TimeWindow) bool
    }

    class TaskType {
        <<enumeration>>
        WALK
        FEEDING
        MEDICATION
        GROOMING
        VET_APPOINTMENT
        ENRICHMENT
        TRAINING
        OTHER
    }

    class Priority {
        <<enumeration>>
        CRITICAL
        HIGH
        MEDIUM
        LOW
    }

    class TaskStatus {
        <<enumeration>>
        PENDING
        SCHEDULED
        COMPLETED
        SKIPPED
        OVERDUE
    }

    class Task {
        +String task_id
        +String pet_id
        +String name
        +TaskType task_type
        +Priority priority
        +TaskStatus status
        +int duration_minutes
        +TimeWindow preferred_window
        +bool is_recurring
        +String recurrence_rule
        +datetime due_datetime
        +String notes
        +mark_complete() None
        +mark_skipped(reason String) None
        +is_overdue() bool
        +get_urgency_score() float
        +generate_next_occurrence() Optional~Task~
    }

    class ScheduledTask {
        +String scheduled_task_id
        +Task task
        +datetime start_time
        +datetime end_time
        +String reasoning
        +bool is_conflict
        +get_duration() int
        +conflicts_with(other ScheduledTask) bool
    }

    class DailySchedule {
        +String schedule_id
        +String owner_id
        +date schedule_date
        +List~ScheduledTask~ scheduled_tasks
        +List~Task~ unscheduled_tasks
        +int total_time_used_minutes
        +String summary
        +add_scheduled_task(st ScheduledTask) None
        +add_unscheduled_task(t Task) None
        +get_schedule_by_pet(pet_id String) List~ScheduledTask~
        +get_completion_rate() float
        +sort_by_time() List~ScheduledTask~
        +sort_by_priority() List~ScheduledTask~
        +filter_by_status(status TaskStatus) List~ScheduledTask~
        +filter_by_pet(pet_id String) List~ScheduledTask~
        +to_dict() dict
    }

    class SchedulerConfig {
        +int day_start_hour
        +int day_end_hour
        +int buffer_minutes_between_tasks
        +bool respect_preferred_windows
        +bool allow_task_splitting
        +String optimization_strategy
    }

    class Scheduler {
        +String scheduler_id
        +Owner owner
        +SchedulerConfig config
        +List~Pet~ pets
        +generate_daily_schedule(date date) DailySchedule
        +prioritize_tasks(tasks List~Task~) List~Task~
        +fit_tasks_to_window(tasks List, available_minutes int) List~ScheduledTask~
        +check_conflicts(schedule DailySchedule) List~ScheduledTask~
        +explain_plan(schedule DailySchedule) String
        -_score_task(task Task) float
        -_apply_time_constraints(task Task) bool
        -_calculate_available_slots() List~TimeWindow~
        -_build_reasoning(task Task, minutes_remaining int) String
    }

    class TaskRepository {
        +Dict tasks
        +add_task(task Task) None
        +get_task(task_id String) Task
        +update_task(task_id String, updates dict) None
        +delete_task(task_id String) None
        +get_tasks_for_pet(pet_id String) List~Task~
        +get_overdue_tasks(pet_id String) List~Task~
    }

    class NotificationService {
        +List~str~ notification_log
        +send_reminder(task ScheduledTask) None
        +send_daily_summary(schedule DailySchedule) None
        +alert_overdue(task Task) None
    }

    Owner "1" --> "0..*" TimeWindow : preferences
    Owner "1" --> "1..*" Pet : owns
    Pet "1" --> "0..*" Task : has
    Task --> TimeWindow : preferred window
    Task --> TaskType : categorized by
    Task --> Priority : ranked by
    Task --> TaskStatus : tracked by
    ScheduledTask --> Task : wraps
    DailySchedule "1" --> "0..*" ScheduledTask : contains
    DailySchedule "1" --> "0..*" Task : unscheduled
    Scheduler --> Owner : manages for
    Scheduler --> SchedulerConfig : configured by
    Scheduler ..> DailySchedule : generates
    Scheduler ..> TaskRepository : queries
    Scheduler ..> NotificationService : triggers
    Scheduler ..> TimeWindow : resolves slots
    TaskRepository "1" --> "0..*" Task : stores