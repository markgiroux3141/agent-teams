# Frontend Proposal

## My slice

I propose a **static HTML/CSS/JS site** with vanilla JavaScript, no build step, no framework.

**Page structure:**
- Single HTML file (`src/index.html`) that loads the recipe data and renders it dynamically
- Recipe list displayed as a responsive card grid on page load
- Clicking a recipe card opens a modal with the full recipe details
- Search and category filter controls in the header; filtering is client-side with vanilla JS
- Modal closes on click-outside or an explicit close button

**Markup style:**
The view uses semantic HTML with clean class-based hooks for styling. Example card structure:

```html
<div class="recipe-list">
  <article class="recipe-card" data-recipe-id="1">
    <h2 class="recipe-card__title">Chocolate Chip Cookies</h2>
    <span class="recipe-card__category">dessert</span>
    <span class="recipe-card__time">45 mins</span>
    <p class="recipe-card__description">...</p>
    <button class="recipe-card__action">View Recipe</button>
  </article>
  <!-- more cards -->
</div>

<div class="recipe-detail-modal" hidden>
  <div class="recipe-detail-modal__content">
    <button class="recipe-detail-modal__close">×</button>
    <h1 class="recipe-detail__title">...</h1>
    <!-- full recipe details -->
  </div>
</div>
```

**Interactivity:**
- Vanilla JS handles card clicks, modal open/close
- Backend provides utility functions (filterByCategory, search, sortByTime) that I call on user interaction
- Data is loaded from `recipes.json` and hydrated into the page on load
- No external dependencies (React, Vue, etc.)

**Why this stack:**
- 8–10 recipes with a simple card grid is a small scope; static HTML/JS is proportional
- No build pipeline, no npm install, no bundler — stakeholder can open the file in a browser immediately
- Vanilla JS is fast and has zero overhead for this use case
- Client-side search/filter is simple to implement in JS and gives snappy interactivity

## What I need from others (CONTRACTS LOCKED)

**From backend:**
- **LOCKED**: Deliver `src/recipes.json` as a JSON array of recipe objects
- **LOCKED**: Provide utility functions in `src/recipeUtils.js` (or similar) for filtering and searching: `filterByCategory(recipes, category)`, `search(recipes, query)`, `sortByTime(recipes)`
- Recipe schema includes: `id`, `name`, `category`, `time`, `servings`, `description`, `ingredients` (array of strings), `steps` (array of strings), plus optional `difficulty` and dietary tags
- I fetch `recipes.json` on page load and call your utility functions when the user interacts with search/filter dropdowns

**From UX:**
- **LOCKED**: BEM-style CSS classes are the styling surface. I'll emit these class names; you style them with plain CSS
- **LOCKED**: `.recipe-list` is flexbox-ready; you apply grid layout rules and responsive breakpoint (768px) via CSS
- **LOCKED**: `.recipe-card` contains title + category + time + description (1–2 sentences max); you handle spacing and visual hierarchy via CSS
- Classes you'll style against:
  - `.recipe-list`, `.recipe-card`, `.recipe-card__title`, `.recipe-card__time`, `.recipe-card__category`, `.recipe-card__description`, `.recipe-card__action`
  - `.recipe-detail-modal`, `.recipe-detail-modal__content`, `.recipe-detail-modal__close`
  - `.recipe-detail__*` for detail modal internals (title, ingredients-list, steps-list, etc.)
  - `.search-input`, `.category-filter`, `.app-header`
- I'll define CSS custom properties (CSS variables) for semantic tokens (e.g., `--color-accent`, `--font-serif`); you populate them with your color palette and typography choices

**From writer:**
- 8 recipes with `name`, `category` (breakfast/main/dessert), `time` (minutes), `servings`, `description` (1–2 sentences), `ingredients` (list), `steps` (list)
- These feed into `recipes.json` which backend delivers and I consume

## Open decisions for the team

1. **Images on recipe cards?**
   - UX brief suggests: either no images (rely on typography), or a unicode/icon glyph per category
   - I propose **no images** for the list view (simpler data, no brittle URLs)
   - If UX wants a glyph per category on the detail modal, they can add via CSS `::before` pseudo-element

2. **Search vs. category filter only?**
   - I propose **both**: search bar (text match on title/description) + category filter dropdown
   - Keeps the UI clean but gives good discoverability
   - Alternatively: category filter only if the team prefers simplicity

3. **Sort controls?**
   - I propose optional sort (e.g., by time, alphabetical) but no sort UI unless the team wants it
   - Backend utility function `sortByTime()` is ready if we add a sort dropdown later

4. **Dietary tags or optional fields?**
   - Writer brief mentions optional `difficulty` and dietary tags (vegetarian, gluten-free)
   - Include if writer wants to use them, skip if not needed to simplify the initial scope
