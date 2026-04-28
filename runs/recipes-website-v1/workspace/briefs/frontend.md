# Frontend dev brief

You're the frontend dev on this small team. The ask is "build a
recipes website" with no further detail.

## What you're responsible for

- HTML structure: page layout, semantic markup, the DOM skeleton
  that backend's JS populates and ux's CSS styles.
- Naming the CSS classes that ux will target. You own the
  class-naming contract.
- Page shape: one page or two? (List view + detail view, vs. all
  inline.)

## What's on your mind

- The site has to open from `file://` (double-click index.html). No
  dev server. That means no JS module imports, no `fetch` of local
  files in most browsers.
- Framework question: the team is small and the scope is small. You
  lean strongly toward **vanilla HTML + CSS + one small JS file**.
  React or Vue would need a build step. Don't fight for a framework
  unless you have a specific reason — you don't.
- A single `index.html` with the recipe list + detail-on-click (via
  a modal or expanding card) is simpler than two HTML files with
  navigation between them. Propose that unless the team pushes back.
- Class naming: pick a consistent prefix (e.g. `rx-`) so ux can
  target your markup cleanly. Think through the major elements:
  page header, recipe card, card title, card meta (time /
  category), card image placeholder, detail view container,
  ingredients list, steps list, search input, category filter.

## What you need from others

- From ux: confirm the class naming convention you propose is
  what they want to style against.
- From backend: confirm the DOM hooks they need (search input id,
  filter button classes, recipe-card-list container id) match
  what you're planning to emit.

## What you should NOT try to own

- CSS values — only class names. Colors, spacing, typography are
  ux's choices.
- The data shape — that's backend. You just declare where to put it.
- Recipe content — that's writer.
