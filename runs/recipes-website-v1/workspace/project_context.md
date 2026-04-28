# Project — recipes website

**Ask:** "Build us a recipes website."

That's it. That's the brief. The stakeholder gave us no further detail
and is unreachable today. We have the rest of the day to ship
something we can show them tomorrow.

## What we know implicitly

- It's a website. It needs to run in a browser.
- It's about recipes. There needs to be recipe content on it.
- "Us" means this small team: one backend dev, one frontend dev, one
  ux designer, one recipe writer, plus me (tech lead / PM).
- No infrastructure — the team has a shared workspace directory. No
  servers, no deployments, no package managers, no build pipeline.
  Whatever we produce has to be a static site that opens by
  double-clicking `index.html`.

## What we don't know (the team must decide)

- How many recipes?
- What categories / structure?
- Visual style?
- Framework? (The tech lead will strongly discourage anything that
  needs a build step, because we can't run one here.)
- How recipes are stored, loaded, filtered.
- What interactivity, if any (search? filter? sort?).
- Single-page or multi-page?

## The process

The team will go through two rounds of deliberation:
1. Each role proposes their slice and what contracts they need from
   the others.
2. Backend writes a SPEC.md that codifies every team-level decision.

Then the team BUILDS in parallel with no further coordination. This
is deliberate: we're testing whether the SPEC is tight enough.

## What success looks like

- `workspace/index.html` opens in a browser and shows a recipes list
  with styling and actual recipe content.
- Clicking a recipe (if detail pages were in scope) shows the full
  recipe.
- No JavaScript errors in the console on load.
- The site feels intentional — a choice of style, not a random mix.

## Output

`OUTPUT.md` — the lead's report covering what was built, files
produced, any contract violations caught, and the view command.
