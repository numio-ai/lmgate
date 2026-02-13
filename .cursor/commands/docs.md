---
description: Workflow for updating project documentation after task completion
---

1. **Review Changed Code**
   - Identify what functionality has changed or been added.
   - List affected modules and components.

2. **Update README.md**
   - If there are new installation steps, usage instructions, or major features, update `README.md`.

3. **Update Technical Documentation**
   - Check `docs/` folder for relevant design documents or API references.
   - Update `CLAUDE.md` if project guidelines, agent behaviors, or common commands have changed.

4. **Cross-check Code Comments**
   - Verify that public interfaces (functions, classes) have up-to-date docstrings matching the implementation.
   - Confirm that any addressed TODOs or FIXME comments have been removed.

5. **Verify Documentation**
   - Read through the changes to ensure clarity and correctness.
   - If generated docs are used, regenerate them to ensure they build correctly.
