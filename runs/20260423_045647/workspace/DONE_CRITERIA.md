# Done Criteria & Scope

## The vague goal (from stakeholder)
"Build us a recipes website."

That's it. No further detail. Unreachable today. Team must decide everything else.

## The roster
- **backend** — data schema, client-side search/filter logic, writes SPEC.md in Phase 2.
- **frontend** — HTML structure, routing, interactivity, CSS class contracts.
- **ux** — visual style (colors, typography, layout, responsive behavior).
- **writer** — recipe content (ingredients, steps, descriptions, tone).

## Ground rules

### Output is a STATIC site
- No server, no build step, no package manager.
- Users open `workspace/index.html` directly via double-click in a browser.
- Works from `file://` protocol with no local fetch limitations.

### Technology constraints
- **Vanilla HTML/CSS/JS is the default.** A framework is only allowed if the team can execute it with zero build step — they cannot, so no React, Vue, webpack, etc.
- **All file paths are relative.** No absolute URLs to external CDNs, except optional Google Fonts for typography.
- **Images**: must use emoji/unicode placeholders OR external https URLs (unsplash, etc.). Team cannot produce binary files.

### What success looks like
- `workspace/index.html` opens in a browser and shows a recipes list with styling and actual recipe content.
- Clicking a recipe (if detail pages were in scope) reveals the full recipe.
- No JavaScript errors in console on load.
- The site feels intentional — a choice of style, not a random assemblage.

## Deliverable
`OUTPUT.md` — the lead's final report with file inventory, contract compliance, and view command.
