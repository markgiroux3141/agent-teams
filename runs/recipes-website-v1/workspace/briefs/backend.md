# Backend dev brief

You're the backend / data dev on this small team. The ask is "build
a recipes website" with no further detail.

## What you're responsible for

- The data layer: how recipes are represented, stored, loaded.
- Any client-side logic (search, filter, sort, routing) that makes
  the site functional beyond static browsing.
- Phase 2: you write `SPEC.md`. You're the technical arbiter.

## What's on your mind

- There's no server and no build step. That constrains us. Options
  for data:
  - Separate JSON file loaded via `fetch()` — clean, but `fetch`
    against `file://` is blocked in most browsers for security. If
    the site must open via double-click, this fails.
  - Inline data in a `<script>` tag (as a global `const RECIPES
    = [...]`). Works on `file://`, but then writer's content has
    to be embedded in a JS file, not a pure data file.
  - Inline data in a `<script type="application/json">` tag, read
    by JS. Works on `file://`, keeps writer's content in
    JSON-shaped form.
  - A build step to inline everything — no, we can't run that.
- Suggest the `<script type="application/json">` approach in your
  proposal — it lets writer produce pure JSON content that lives in
  the HTML file (frontend includes it as a block), and JS reads it
  via `document.getElementById('recipes-data').textContent`.
  Alternatively, have writer produce `data/recipes.json` and have
  backend inline it at the top of `app.js` as a const. Think about
  which is cleaner.

## What you need from others

- From writer: field list per recipe. Confirm the schema covers
  what they want to say.
- From frontend: the DOM structure they'll emit so you know where
  your JS is injecting content.
- From ux: nothing blocking; they design to frontend's classes.

## What you should NOT try to own

- CSS. That's ux.
- HTML layout. That's frontend.
- Recipe content itself. That's writer.
