---
description: Foundational behavioral principles for AI agents. Must always be followed by all agents.
alwaysApply: true
---


# CRITICAL RULES

## Have laser focus on current task
When work on tasks you must laser focus only on one task you're working on. Never get distracted to additional cosmetic improvements like better formatting or better logs, unless user explicitely asked you to do. Your are at your best solving one problem at a time. 

## Strictly follow design pricnciples
- YAGNI: never add additional functionality which is not directly related to your task. Inform user when you identify additional opportunities for improvemnets, provide your recommendations. But never mix two unrelataed modifications in one commit. E.g. if you work in implementing feature and identified more flexible way to configure the code, you first complete your main task, and give user your recommendations for optimiztion. If user agrees, you will work on optimization as separate task. 
- KISS: keep your soltuions simple. You're successful when your code is well structured, maintanable, and simple. 


## Behavior when executing complex plans
- Always explain your steps to user before you proceeed to execution
- When plan consists of multiple steps, and each steps involves multiple changes or risky changes, you must review step outcomes with users, and seek for feedback. 
- You must get explicit user approval to proceed to next steps, after you reviewd with user results of previous step and confirmed successful completion. 

## Troubleshooting:
- Always look for root cause - Take systematic approach.
- Fix root cause first - Never start with workarounds.
- Minimize code changes - The less you modify, the better.

## Code Generation Guidelines
- Follow existing code patterns in the repository
- Include appropriate error handling
- Add comments for complex logic
- Write tests for new functionality

## Documentation Guidelines
- Update README files when adding new features
- Create ADRs for significant architectural decisions in the 'docs' folder
- Keep specifications updated during implementation in the 'docs' folder

## Planning Guidelines

Plans are requirements documents, not implementation guides. The agent derives the implementation from requirements.

### Plan Structure
A proper plan MUST contain:
- **Problem statement**: What problem are we solving and why
- **Objective**: Desired end state
- **Requirements**: Numbered (R1, R2, ...) with measurable specifications
- **Acceptance criteria**: Testable conditions that prove completion
- **Risks and mitigations**: What could go wrong

A proper plan MUST NOT contain:
- Implementation code (no HCL, Python, bash, etc.)
- Exact variable names or function signatures
- Step-by-step implementation instructions
- Line-by-line changes

### Separation of Concerns
| Document | Contains | Does NOT contain |
|----------|----------|------------------|
| Plan | WHAT and WHY | HOW (implementation) |
| Code | HOW (implementation) | Requirements rationale |

### Example: Good vs Bad Requirements

**Bad** (implementation detail):
```
Add this code to main.tf:
resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_subnet.first.availability_zone
  size = var.data_volume_size
  ...
}
```

**Good** (requirement):
> R1: Persistent EBS Volume
> - One volume per host, named `{host}-data`
> - Type: gp3, Size: 50 GB (configurable)
> - Lifecycle: `prevent_destroy = true`

### Rationale
- Plans outlive implementations - requirements remain valid even if implementation changes
- Agents can find better solutions when not constrained by prescribed code
- Code review focuses on "does it meet requirements?" not "does it match the plan?"
- Plans are readable by non-technical stakeholders

