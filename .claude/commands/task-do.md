---
description: Workflow for executing a task
---

# Task-Do Workflow

## Usage
Invoke with: `/task <task-file>`

Example: `/task-do @tasks/backlog/20260118_add_persistent_ebs_volumes.md`

## Task
Work on the specified task file following the task management standard in `@docs/task-management.md`.

## Execution Steps

1. **Activate the task**
   - Move the task file to `tasks/active/`
   - Set `status: active` in the task file YAML header

2. **Read and understand the task**
   - Read the task file
   - Strictly follow rules in `first-principles.md`

3. **Execute the task**
   - Disambiguate by asking for clarification if needed
   - Plan multi-step work and get approval before execution
   - Execute one step at a time with user verification for risky changes

4. **Complete the task (after user confirms)**
   - Set `status: done` in the task file YAML header
   - Move task file to `tasks/done/` directory

## Rules

- Follow all rules in `CLAUDE.md`
- Single-task discipline: focus only on the specified task
- YAGNI/KISS: no unrelated improvements
- Get explicit approval before multi-step or risky changes
- Troubleshooting: root cause first, minimize changes
