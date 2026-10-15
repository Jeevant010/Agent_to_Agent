# Agent Guidelines

## Anti-Slop Activation

Whenever a task touches frontend code, user interfaces, styling, or user-facing copy (such as React, Vue, Next.js, HTML, CSS, Tailwind, or mobile web views):

1. **Trigger:** Load the `antislop` core skill before planning, writing, or reviewing UI code.
2. **Sub-skills:** Load the specific sub-skills matching the task scope:
   - `antislop-ui`: Visual layout, color tokens, typography, component hierarchy, and animations.
   - `antislop-layoutmobile`: Breakpoints, responsive grids, tap targets, and overflow prevention.
   - `antislop-human`: WCAG AA contrast (4.5:1 text, 3:1 large), keyboard focus outlines, and screen reader labels.
   - `antislop-copywriting`: Headings, CTAs (no generic "Get Started"), empty states, and microcopy (no em dashes).
   - `antislop-code`: Comment hygiene and stripping boilerplate explanations.
3. **Execution Mode:**
   - Use `during` mode by default when building or modifying components so every visual element passes the purpose test and has functional interactivity.
   - Use `after` mode when asked for an audit, code review, or inspection, generating a prioritized findings list before making edits.

## Documentation and Context Management

- **New Chat or Context Window Pressure:**
  - Read relevant documents in `docs/` at the start of a new chat session to load project state and architectural context.
  - When nearing context limits or losing track of prior steps, review `docs/` and summarize or compact before proceeding.
- **Continuous Documentation Updates:**
  - Whenever a new feature, architecture change, or core component is built or modified, update or create the corresponding documentation in `docs/` in the same change.
  - Document the design decisions, component contracts, and current project status so future sessions have an accurate reference.

