---
status: done
---

# Improve documenbtation and rules

**Date**: 2026-02-20

## Context

Our current document "@LMGate User Guide" combines user and developer documentation. This is not a good practice. We need to have dedicated documentation for users and developers. We will use @README.md file as user documentation and @DEVELOPMENT.md file as developer documentation. We also need to improve @CLAUDE.md file. @CLAUDE.md must (1) refer to @README.md file for user documentation and DEVELOPMENT.md file for developer documentation, (2) refer to other documentation in 'docs' directory. It also need to be updated to reflect the current state of the project.

## Task
- Create @README.md file as user documentation, using "@LMGate User Guide" as a source , and extend it with additional information.
- Create @DEVELOPMENT.md file as developer documentation, using "@LMGate Developer Guide" as a source , and extend it with additional information.
- Update @CLAUDE.md file to refer to @README.md and @DEVELOPMENT.md files and other documentation in 'docs' directory. It also need to be updated to reflect the current state of the project. It should refer to @README.md and @DEVELOPMENT.md files, and other documentation in 'docs' directory, and doesn't duplicate information. However if other documents lack details important for AI agents, @CLAUDE.md provides it.

## Acceptance Criteria

- [ ] @README.md file provide clean, brief, nonumbiguous documentation that will allow user not familiar with the LMGate implementation details quickly install, configure and use it. There should be briaf 'Quick start' section, followed by sections with detailed instructions.
- [ ] @DEVELOPMENT.md file as developer documentation. It should provide detailed instructions for developers to understand the LMGate implementation details. It shouldn't repeat information from other documents from 'docs' directory, but refer to them, and add additional information that is not present in other documents.
- [ ] @CLAUDE.md file contains up-to-date details about project and its components. It referes to @README.md and @DEVELOPMENT.md files and other documentation in 'docs' directory, and doesn't duplicate information. However if other documents lack details important for AI agents, @CLAUDE.md provides it.
