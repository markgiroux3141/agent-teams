# Project — recipes website

**Ask:** "Build us a recipes website."

That's it. That's the brief. The stakeholder gave us no further detail
and is unreachable today.

## What we know implicitly

- It's a website. It needs to show recipes.
- "Us" means this small team: one backend dev, one frontend dev, one
  ux designer, one recipe writer, plus me (tech lead / PM).
- The output is code the stakeholder can take and run somewhere.
  We produce source files in the workspace; we do NOT deploy, host,
  install packages, or run anything. Stack, framework, deployment
  model — all the team's call.

## What we don't know (the team must decide)

- How many recipes? What categories?
- What stack? Static HTML/CSS/JS? A React or Vue SPA? A server-
  rendered site (FastAPI + Jinja, Rails, Go templates, etc.)?
  A headless-CMS-style SSG? Something else? Pick whatever fits
  the scope; defend the choice in Phase 1.
- Visual style.
- How recipes are stored, loaded, searched, filtered.
- What interactivity, if any.
- Routing: single page with detail-on-click, multi-page, dynamic
  routes, etc.

## The process

The team will go through two rounds of deliberation:
1. Each role proposes their slice and what contracts they need from
   the others.
2. Backend writes a SPEC.md that codifies every team-level decision
   — stack, file layout, naming contracts, schema, handoffs.

Then the team BUILDS in parallel with no further coordination. This
is deliberate: we're testing whether the SPEC is tight enough.

## What success looks like

- The team converges on a stack and captures every cross-role
  contract in SPEC.md.
- All four teammates produce their slice under `workspace/src/`
  without colliding or drifting.
- The lead's verification catches any contract drift explicitly.
- OUTPUT.md explains how the stakeholder would build/run the code.

## Output

`OUTPUT.md` — the lead's report covering what was built, the stack
chosen, files produced, any contract violations caught, and how the
stakeholder would run the code given the chosen stack.
