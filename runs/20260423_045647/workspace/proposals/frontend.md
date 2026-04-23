# Proposal — Frontend

## My slice

I will produce `index.html` (single page) with vanilla HTML, a DOM skeleton that backend's JS can populate with recipe data, and a consistent set of CSS classes that ux will style.

**Page design:**
- Single `index.html` file that opens via double-click
- Recipe list view at page load (grid of recipe cards)
- Clicking a card opens a modal detail view (stays on same page)
- Search input at the top for full-text search
- Category filter buttons (breakfast, main, dessert, etc.)
- No navigation between pages; modal close returns to list

**HTML structure:**
- Semantic markup: `<main>`, `<article>` for cards, `<section>` for ingredient/step lists
- No inline styles or onclick handlers — all class-based hooks for ux and backend
- Responsive meta tag, basic accessibility (alt text patterns, label associations)

**CSS class system:**
Prefix: `rx-` (recipes). Major classes:

```html
<!-- Page header -->
<header class="rx-header">
  <h1 class="rx-title">Recipes</h1>
  <input id="search-input" type="text" placeholder="Search..." class="rx-search-input">
  <div class="rx-filter-buttons">
    <button class="rx-filter-button" data-category="breakfast">Breakfast</button>
    <button class="rx-filter-button" data-category="main">Main</button>
    <button class="rx-filter-button" data-category="dessert">Dessert</button>
  </div>
</header>

<!-- Recipe list grid -->
<main class="rx-main">
  <div id="recipe-list" class="rx-recipe-list">
    <!-- Backend injects <article class="rx-card"> elements here -->
    <article class="rx-card" data-recipe-id="1">
      <div class="rx-card-image">🍳</div>
      <h2 class="rx-card-title">Scrambled Eggs</h2>
      <div class="rx-card-meta">
        <span class="rx-card-time">5 min</span>
        <span class="rx-card-category">breakfast</span>
      </div>
      <p class="rx-card-description">Creamy, simple, never fails.</p>
    </article>
  </div>
</main>

<!-- Detail modal (hidden by default, shown on card click) -->
<div id="recipe-detail" class="rx-detail-modal rx-detail-modal--hidden">
  <div class="rx-detail-content">
    <button id="detail-close" class="rx-detail-close">×</button>
    <h2 class="rx-detail-title">Recipe Title</h2>
    <div class="rx-detail-meta">
      <span class="rx-detail-time">30 min</span>
      <span class="rx-detail-servings">Serves 4</span>
      <span class="rx-detail-category">main</span>
    </div>
    <p class="rx-detail-description">Full description here.</p>
    
    <section class="rx-detail-section">
      <h3 class="rx-detail-heading">Ingredients</h3>
      <ul id="ingredients-list" class="rx-ingredients-list">
        <!-- Backend injects <li> items -->
      </ul>
    </section>
    
    <section class="rx-detail-section">
      <h3 class="rx-detail-heading">Steps</h3>
      <ol id="steps-list" class="rx-steps-list">
        <!-- Backend injects <li> items -->
      </ol>
    </section>
  </div>
</div>
```

**File structure:**
- `index.html` — everything above
- `styles.css` — all styling (ux owns this)
- `app.js` — all JS logic and interactivity (backend owns this)

## What I need from others (contracts)

### From backend:
- **Data format & location**: You decide if recipes data is inline `<script type="application/json">` in HTML, or baked into `app.js` as a const. Tell me which, so I know what's expected.
- **JS injection points**: Confirm I've provided the right container IDs (`recipe-list`, `ingredients-list`, `steps-list`) and that my class names match what you'll query.
- **Event hooks**: Confirm search-input `id="search-input"` and filter buttons with `data-category` attributes are what you need to wire event listeners.
- **Data schema**: What fields does each recipe have? I need to know so I can emit the right class names for each field in the card template (e.g., `rx-card-time`, `rx-card-category`, `rx-card-description`).

### From ux:
- **Image handling**: Do you want emoji/unicode glyphs in the `rx-card-image` divs, or no image area at all? I'll include the div either way, but your choice affects how you style the card layout.
- **Class name confirm**: Do the `rx-` prefix and class names above feel right to style against?
- **Responsive breakpoint**: You mentioned 768px as the collapse point (list → single column). I'll assume that's your target; confirm if you need different.
- **Detail modal behavior**: Should the modal be a full-screen overlay, or a centered box? I'll provide the base structure; you style it. Just confirm no surprising expectations.

### From writer:
- **Content density**: How long are your recipe descriptions (your brief says 1–2 sentences)? I size `rx-card-description` accordingly.
- **Recipe count & categories**: You proposed 8 recipes in breakfast/main/dessert. Confirm final count and any 4th category (snack, side?) so backend knows the filter buttons to emit.

## Open decisions for the team

1. **Detail view modality**: Full-screen overlay or centered modal box?
   - *My preference: centered modal with semi-transparent backdrop, keeps focus tight.*

2. **Category filter: multi-select or single?**
   - *My preference: single category at a time (one button active), simpler UX. But if you want multi-select, I'll adjust the structure.*

3. **Empty state messaging**:
   - If search returns no results, should the page show "No recipes found" or similar?
   - *My preference: yes, small message in the recipe-list area.*

4. **Image handling** (flagged to ux, but team decision):
   - Emoji glyphs per category, or skip images and rely on typography?
   - *My preference: emoji. Clean, works offline, no external requests.*

5. **Recipe detail: inline or modal?**
   - *Decision made (modal), but flagging in case team prefers separate recipe.html pages.*
   - Single-page modal is simpler and avoids complex routing; I recommend keeping it.
