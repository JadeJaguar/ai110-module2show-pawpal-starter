# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

    My initial design had four classes: Owner, Pet, Task, and Schedule. Owner holds basic profile info and a list of pets, Pet holds the animal's info and its associated tasks, Task represents a single care activity with a name, duration, and priority, and Schedule takes those tasks and produces a daily plan.

**b. Design changes**

- Did your design change during implementation?
    Yes 
- If yes, describe at least one change and why you made it.
    
    As the design evolved from concept to implementation, it became clear that four classes weren't enough to support real scheduling logic. Each new class solved a specific gap: ScheduledTask was needed to attach a start and end time to a task once placed, DailySchedule was needed to track both what fit and what didn't, TimeWindow was needed to represent when the owner is actually available, and SchedulerConfig was needed to make the scheduler's behavior adjustable. The three enums (TaskType, Priority, TaskStatus) were added to keep task data consistent and prevent errors from free-text strings.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

    The scheduler considers three constraints: available time (the owner sets a daily minute budget and no task is placed if it would exceed it), task priority (each task has a CRITICAL/HIGH/MEDIUM/LOW level that drives its urgency score), and due time (tasks that are overdue get a +10 score bonus, and tasks due within 2 hours get a +2 bonus, so urgency increases as deadlines approach). Preferred time windows can be stored on each task, but the current scheduler does not enforce them during placement, that is a known gap.

    Available time was treated as the hardest constraint because there is no way around it: if the owner only has 2 hours, the schedule cannot physically exceed that. Priority was treated as the most important ordering constraint because pet care tasks have real health consequences, a missed medication is more serious than a missed grooming session, so the algorithm needs to protect high-priority tasks first. Due-time bonuses were added on top of priority so that an upcoming deadline can temporarily elevate a normally lower-priority task above one that has no deadline pressure.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

    **Tradeoff: Greedy scheduling over an optimal search**

    The scheduler uses a greedy algorithm, it sorts all tasks by urgency score once, then places them into time slots in that order, taking the first slot that fits and never revisiting earlier decisions. This means it can miss arrangements that would fit more tasks overall. For example, if a 60-minute LOW priority task is somehow scored first, it could block three 20-minute HIGH priority tasks from fitting, even though dropping the LOW task would have allowed all three in.

    This tradeoff is reasonable for a daily pet care app for several reasons. First, tasks are sorted by priority before placement, so the greedy order closely mirrors what a human would choose anyway, critical and high-priority tasks go first. Second, the scheduler runs in milliseconds on a small list (5-20 tasks), so there is no performance pressure that would justify a more complex algorithm like dynamic programming or backtracking. Third, pet owners reviewing the schedule can manually override start times or adjust available minutes, so a "good enough" automated plan that they can tweak is more practical than a theoretically optimal plan that takes longer to compute and harder to explain.

    The main cost of this tradeoff is that the scheduler only checks for exact time-slot overlap after the fact (via `check_conflicts()`), rather than proactively finding a conflict-free arrangement. A future improvement would be to enforce preferred time windows during placement, so tasks the owner flagged for a specific time of day are placed there rather than stacked at the start of the day.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

    AI was used across every phase: generating the initial class structure from the UML, implementing scheduling logic, writing the full test suite, debugging UI bugs in Streamlit (such as the progress bar lag and the session state conflict on the owner selector), and syncing the UML diagram with the final code. The most helpful prompts were specific and scoped, for example, describing the exact bug behavior rather than just saying "it doesn't work," or asking for a test plan before writing any tests.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

    I verified AI-generated code by running it directly (pytest, streamlit run) and reading the output rather than assuming it was correct. The Streamlit session state error on the remove owner button is a good example: the AI's first fix used an inline button handler that failed, and the error trace pointed to exactly why, which led to the callback-based fix.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

    31 tests across six groups: urgency scoring, task prioritization, greedy scheduling, conflict detection, recurring task generation, and sorting/filtering. These cover the core logic end-to-end, a wrong urgency score or broken conflict check directly affects the quality of the schedule the owner receives.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

    Confidence is 4/5 for the backend logic. All 31 tests pass and cover the main code paths including edge cases like empty lists, exact-fit budgets, and unknown recurrence rules. The gap is the UI layer — there are no automated tests for the Streamlit interface, so bugs like the progress bar lag and the session state error were only caught manually. If I had more time I would test: an owner with zero available minutes, two recurring tasks that both complete on the same day, and a schedule regenerated after a pet is removed mid-session.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

    The backend logic layer. The scheduler, urgency scoring, conflict detection, and recurring task generation all work correctly and are fully tested. The separation between `pawpal_system.py` and `app.py` made it easy to test the core behaviors independently and debug UI bugs without touching the scheduler.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

    I would redesign the UI side, I would make the app less cluttered by moving forms into popups and using a sidebar for navigation, so the main view stays focused on the schedule. I would also add a dedicated section to edit pet profile information after it has been created.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

    AI is most useful when you already have a clear picture of what you want and use it to move faster, not when you hand it an open-ended problem and accept whatever comes back. Every time I gave a specific, scoped prompt the output was accurate and usable. Every time the scope was vague, the output needed significant review or correction.
