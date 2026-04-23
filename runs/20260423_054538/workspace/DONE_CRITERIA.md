# Recipes Website — Phase 0 Scope & Process

## The Goal

Build us a recipes website. That's the brief. The stakeholder gave us no further detail and is unreachable today.

We produce source code in the workspace. We do NOT deploy, host, install packages, or run anything. The output is code the stakeholder can take and run somewhere else.

## The Team

- **backend**: Backend dev. Owns data schema + client-side search/filter. Writes SPEC.md in Phase 2.
- **frontend**: Frontend dev. Owns HTML structure, routing, interactivity.
- **ux**: UX designer. Owns visual style: colors, typography, layout, responsive behavior.
- **writer**: Recipe writer. Owns recipe content: ingredients, steps, tone.

## What the Team Must Decide

The brief gives us a vague goal. The team decides:

- **Stack**: Static HTML/CSS/JS? React SPA? Vue? Server-rendered (FastAPI + Jinja, Rails, Go, etc.)? Headless-CMS SSG? Something else? Defend your choice in Phase 1.
- **Scope**: How many recipes? What categories?
- **Visual style**: Colors, typography, layout, responsive behavior.
- **Data model**: How recipes are stored, loaded, searched, filtered.
- **Interactivity**: What user interactions, if any?
- **Routing**: Single page with detail-on-click? Multi-page? Dynamic routes? etc.

## Process Ground Rules

### The Team Decides the Stack
Static HTML/CSS/JS, React frontend, Vue frontend, Python/Node/Go backend, SSG, server-rendered — all fair game. Your job is NOT to push toward any choice; your job is to make sure the choice is made deliberately and captured in SPEC.md tightly enough for four teammates to build in parallel without further coordination.

### The Team Produces Source Files Only
- No deployment, no running, no installing packages, no network calls, no binary assets.
- The output is code. Whoever receives this workspace later can build/run the code elsewhere.
- Success is NOT "the site opens in a browser" — success is **"four teammates built to a shared contract without colliding"**.

### All Code Lives Under `src/`
- The internal structure of `src/` is the team's call (`src/frontend/`, `src/backend/`, flat, whatever).
- Planning artifacts (SPEC.md, proposals/, OUTPUT.md) stay at the workspace root.
- This separation is housekeeping, not architectural.

## Deliberation Format

### Phase 1: Parallel Proposals (No Dependencies)
Each role writes `proposals/<role>.md` in this format:

```
## My slice
- <what I propose to build; be concrete>

## What I need from others (contracts)
- <from backend: ...>
- <from frontend: ...>
- <from ux: ...>
- <from writer: ...>

## Open decisions for the team
- <concrete question, with my preferred answer>
```

Use `send_message` liberally to negotiate contracts with peers. This is the negotiation phase.

### Phase 2: SPEC Synthesis (Delegated to Backend)
Backend reads all four proposals, absorbs negotiation traffic, and writes `SPEC.md`.

The SPEC must contain:

1. **Architecture** — one paragraph naming the stack the team agreed on.
2. **File ownership table** — every path owned by exactly one role. All runtime paths prefixed with `src/`.
3. **Recipe data schema** — field names, types, required vs optional.
4. **Cross-role contracts** — ANY shared-naming surface (CSS class names, React component names/props, API endpoints, template variable names, CLI arguments, etc.) that two roles must both observe to integrate.
5. **Content plan** — recipe count, categories, fields per recipe.
6. **Data flow** — how recipe content reaches whatever renders it to the user.
7. **Content handoff (REQUIRED)** — for EVERY file a producer writes, state which runtime file/module loads it and how. If writer produces `recipes.json` but no other file references it, writer's output is orphaned. Name the bridge explicitly.

### Phase 3: Parallel Build (No Further Coordination)
Each role builds their slice per SPEC.md. No cross-team messages during build. Everything needed is in the SPEC.

### Phase 4: Verification
Lead verifies file existence, contract symmetry, content handoff, data schema, and inbound references. Finalizes with a compliance report.

## Success Criteria

1. **All four teammates converge on a stack** during Phase 1 negotiation.
2. **SPEC.md is tight enough** that all four teammates can build in parallel (Phase 3) without further coordination or collisions.
3. **All files are produced as promised** in the ownership table.
4. **All cross-role contracts are honored** (class names, API shapes, handoff paths, schema fields).
5. **Every producer file is referenced** by some consumer file.
6. **OUTPUT.md explains** how to build/run the code given the chosen stack.
