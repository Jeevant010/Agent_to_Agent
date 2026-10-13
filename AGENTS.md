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
