# Recipes Website — SPEC.md

## Architecture

Single-page static site with vanilla HTML/CSS/JavaScript. Recipe list view on load, detail modal on card click. Data embedded in HTML, no server or build step. Opens via file:// protocol (double-click index.html).

---

## File ownership & paths

| Path | Owner | Description |
|------|-------|-------------|
| `index.html` | frontend | Page skeleton, semantic markup, recipe list grid, detail modal, `<script type="application/json" id="recipes-data">` with embedded recipes array |
| `styles.css` | ux | All styling, responsive grid (3 col → 2 col → 1 col), color palette, typography, modal overlay |
| `app.js` | backend | Data loading, search/filter logic, modal open/close, event listeners, DOM injection for recipe cards and detail view |

---

## Recipe schema (JSON)

Each recipe is a JSON object with the following structure:

```json
{
  "id": "string (required, unique identifier, e.g. 'fluffy-pancakes')",
  "name": "string (required, recipe title, 2–4 words)",
  "description": "string (required, 1–2 sentences, practical and warm tone)",
  "category": "string (required, one of: breakfast, main, dessert)",
  "time": "number (required, cooking time in minutes, integer)",
  "servings": "number (required, yield in servings, integer)",
  "ingredients": "array of strings (required, formatted as 'amount unit ingredient', e.g. ['2 cups flour', '1 can chickpeas'])",
  "steps": "array of strings (required, ordered cooking instructions)",
  "difficulty": "string (optional, one of: easy, medium, hard)",
  "dietary_tags": "array of strings (optional, e.g. ['vegetarian', 'gluten_free', 'vegan'])"
}
```

**Example recipe:**
```json
{
  "id": "fluffy-pancakes",
  "name": "Fluffy Pancakes",
  "description": "Golden, tender pancakes with a crispy exterior. Perfect weekend breakfast in 20 minutes.",
  "category": "breakfast",
  "time": 20,
  "servings": 4,
  "ingredients": [
    "2 cups all-purpose flour",
    "2 tablespoons sugar",
    "2 teaspoons baking powder",
    "1 teaspoon salt",
    "2 cups milk",
    "2 eggs",
    "2 tablespoons melted butter"
  ],
  "steps": [
    "Whisk flour, sugar, baking powder, and salt in a large bowl.",
    "In another bowl, whisk milk, eggs, and melted butter until combined.",
    "Pour wet ingredients into dry ingredients and stir until just combined (lumpy is okay).",
    "Heat a buttered skillet or griddle over medium heat.",
    "Pour 1/4 cup batter onto the hot surface for each pancake.",
    "Cook until bubbles form on the surface, then flip and cook until golden brown.",
    "Serve warm with maple syrup and butter."
  ],
  "difficulty": "easy",
  "dietary_tags": ["vegetarian"]
}
```

**Schema notes:**
- `difficulty` and `dietary_tags` are optional; not every recipe requires them.
- Ingredients are flat strings with amounts and units embedded, not structured objects.
- Steps are ordered; backend preserves order when rendering the detail view.

---

## CSS contracts

### Class naming convention

All recipe-related classes use the **`rx-`** prefix (recipes). Frontend commits to emitting exactly these classes; ux styles against them.

### Required class names (locked)

**Page header:**
- `.rx-header` — page header container
- `.rx-title` — main page title (h1)
- `.rx-search-input` — search input field (id: `search-input`)
- `.rx-filter-button` — category filter buttons (attribute: `data-category="breakfast|main|dessert"`)

**Recipe list view:**
- `.rx-recipe-list` — grid container (id: `recipe-list`)
- `.rx-card` — individual recipe card (attribute: `data-recipe-id="[id]"`)
- `.rx-card-image` — emoji glyph placeholder (single character, category-based)
- `.rx-card-title` — recipe name (h2)
- `.rx-card-meta` — metadata container
- `.rx-card-time` — cooking time (e.g. "20 min")
- `.rx-card-category` — category label (e.g. "breakfast")
- `.rx-card-description` — recipe description (paragraph, 1–2 sentences)

**Detail modal:**
- `.rx-detail-modal` — full-screen modal overlay (id: `recipe-detail`, hidden by default)
- `.rx-detail-modal--hidden` — state class when modal is closed
- `.rx-detail-content` — modal inner content box
- `.rx-detail-close` — close button (id: `detail-close`, symbol: "×")
- `.rx-detail-title` — recipe name in modal (h2)
- `.rx-detail-meta` — metadata container in modal
- `.rx-detail-time` — time in modal
- `.rx-detail-servings` — servings in modal (e.g. "Serves 4")
- `.rx-detail-category` — category in modal
- `.rx-detail-description` — full description in modal
- `.rx-detail-section` — section wrapper (ingredients, steps)
- `.rx-detail-heading` — section heading (h3, "Ingredients", "Steps")
- `.rx-ingredients-list` — unordered list of ingredients (id: `ingredients-list`, `<ul>`)
- `.rx-steps-list` — ordered list of steps (id: `steps-list`, `<ol>`)

### Design tokens (from UX proposal)

**Colors (CSS custom properties):**
```css
--rx-bg: #FAF7F2;           /* warm off-white, page background */
--rx-surface: #FFFBF7;      /* soft cream, card backgrounds */
--rx-text-primary: #2B2520; /* dark brown, headings and primary text */
--rx-text-secondary: #6B6459; /* muted brown, metadata labels */
--rx-accent: #C85A17;       /* burnt orange, interactive elements */
--rx-border: #E8E3DC;       /* warm gray, dividers */
```

**Typography:**
- **Headings (`.rx-card-title`, `.rx-detail-title`, `.rx-detail-heading`):** Merriweather, Georgia, serif; font-weight 700; color `--rx-text-primary`
- **Body/UI (`.rx-card-description`, `.rx-detail-description`, lists):** -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height 1.6; color `--rx-text-primary`
- **Metadata (`.rx-card-meta`, `.rx-card-time`, `.rx-card-category`):** system sans; font-size 0.875rem; color `--rx-text-secondary`

**Google Fonts link (frontend adds to `<head>`):**
```html
<link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@700&display=swap" rel="stylesheet">
```
(If Google Fonts fails to load, Georgia fallback renders serif headings.)

**Responsive layout:**
- Desktop (≥1024px): 3-column grid
- Tablet (768–1023px): 2-column grid
- Mobile (<768px): 1-column grid (full width with side margins)

**Touch targets:** Minimum 44×44px for interactive elements (buttons, close affordance).

---

## Content plan

**Recipe count:** 8 recipes total
**Categories:** breakfast (3), main (3), dessert (2)

**Recipe list (proposed by writer):**

| Recipe | Category | Time | Difficulty |
|--------|----------|------|------------|
| Fluffy Pancakes | breakfast | ~20 min | easy |
| Avocado Toast | breakfast | ~10 min | easy |
| Shakshuka | breakfast | ~25 min | medium |
| Grilled Salmon | main | ~30 min | medium |
| Pasta Carbonara | main | ~20 min | medium |
| Chicken Stir-Fry | main | ~25 min | medium |
| Chocolate Lava Cake | dessert | ~20 min | medium |
| Lemon Bars | dessert | ~40 min | easy |

**Content density per recipe:**
- Title: 2–4 words (e.g., "Fluffy Pancakes", "Grilled Salmon")
- Description: 1–2 sentences, practical tone, no marketing language
- Ingredients: 6–12 items, formatted with amounts and units
- Steps: 5–10 clear, conversational instructions
- Difficulty and dietary tags: optional; writer includes where relevant

---

## Page routing & UX flow

**Single-page design (index.html):**
1. User opens index.html in a browser (file:// protocol, no server).
2. Page loads with recipe list visible (grid of `.rx-card` elements).
3. Search input and category filter buttons visible above the grid.
4. Clicking a recipe card opens a full-screen modal with the recipe detail (ingredients, steps, metadata).
5. Clicking the close button (×) or the semi-transparent backdrop closes the modal and returns to the list.
6. Typing in search input or clicking filter buttons re-renders the list in real-time without page reload.

**Modal detail view:**
- Modal is a full-screen overlay with semi-transparent background.
- Content box is centered, scrollable if needed.
- Close affordance: explicit close button (×) in top-right corner, 44×44px minimum.
- Clicking the backdrop (semi-transparent area) also closes the modal (secondary affordance).
- Modal content: recipe title, metadata (time, servings, category), full description, ingredients list, steps list.

---

## Data loading

**Where recipes live:** Embedded in index.html as a `<script type="application/json">` tag.

**Format:**
```html
<script type="application/json" id="recipes-data">
[
  {
    "id": "recipe-1",
    "name": "...",
    ...
  },
  {
    "id": "recipe-2",
    ...
  }
]
</script>
```

**How app.js loads it:**
```javascript
const recipesData = document.getElementById('recipes-data').textContent;
const recipes = JSON.parse(recipesData);
```

**Why this approach:**
- Works from file:// protocol (no fetch limitations).
- No server or build step required.
- Frontend controls where the data lives; writer provides the JSON; backend reads and uses it.
- Data is loaded synchronously on page load, no async issues.

---

## Search & filter behavior

### Search scope and matching
- **Scope:** Search matches against recipe `name`, `description`, and `ingredients` (all three combined).
- **Case sensitivity:** Case-insensitive matching (typing "chick" finds "Chicken Stir-Fry").
- **Partial match:** Substring match (e.g., "sal" finds "Grilled Salmon").
- **Real-time:** Search results update on every keystroke (not submit-on-enter); user sees filtered results as they type.
- **Search field:** `<input id="search-input">` (wired by backend's JS)

### Category filter behavior
**Single-select behavior (not multi-select):**
- Only one category button can be active at a time.
- Clicking a category button activates it (shows active state); clicking the same button again deactivates it.
- At most one `.rx-filter-button` has an active state (e.g., `data-active="true"` or `.rx-filter-button--active` class).
- Filter buttons: data-category="breakfast", data-category="main", data-category="dessert"

### Combined filtering (AND logic)
- When both search AND category filter are active, only recipes matching BOTH conditions are shown.
- Example: if search="salmon" and category="main" are both active, only recipes in the main category with "salmon" in name/description/ingredients are displayed.

### Filter state and rendering
- Backend's app.js maintains current filter state: `currentSearch` (string) and `activeCategory` (string or null).
- On search input event: update `currentSearch` and re-render list.
- On filter button click: toggle `activeCategory` and re-render list.
- Re-rendering: clear the recipe-list container, inject filtered recipe cards.

---

## Detail view content

**In detail modal, display:**
- Recipe title (from `name`)
- Metadata: time, servings, category
- Full description (from `description`)
- **Ingredients section:**
  - Heading: "Ingredients"
  - List: each ingredient as a `<li>` in the `.rx-ingredients-list` `<ul>`
- **Steps section:**
  - Heading: "Steps"
  - List: each step as a `<li>` in the `.rx-steps-list` `<ol>` (ordered)
- **Optional detail view content (if writer provides them):**
  - Difficulty: display as a metadata label (e.g., "Difficulty: medium")
  - Dietary tags: display as small badges or comma-separated labels (e.g., "vegetarian, gluten-free")

---

## Empty state handling

When a search + filter combination returns zero recipes:
- Clear the recipe list container.
- Display a simple message: "No recipes found. Try adjusting your search or filters."
- Frontend emits a placeholder div or paragraph with a class (e.g., `.rx-empty-state`); backend populates it with text.
- UX styles `.rx-empty-state` (centered, secondary text color, appropriate spacing).

---

## Emoji mapping (category → glyph)

Frontend's app.js maintains a hardcoded emoji map (not in data):

```javascript
const categoryEmoji = {
  breakfast: "🍳",
  main: "🍽️",
  dessert: "🍰"
};
```

When rendering a recipe card, frontend looks up the emoji from the category and injects it into `.rx-card-image`.

---

## Implementation checklist (for build phase)

### Frontend (index.html)
- [ ] Single-page HTML skeleton with all `.rx-*` class names
- [ ] Page header, search input, filter buttons
- [ ] Recipe list container (`id="recipe-list"`)
- [ ] Recipe card template structure (`.rx-card` with nested classes)
- [ ] Detail modal skeleton (`id="recipe-detail"`)
- [ ] `<script type="application/json" id="recipes-data">` with recipes array
- [ ] Google Fonts link in `<head>`
- [ ] Responsive meta tag, semantic markup

### UX (styles.css)
- [ ] CSS custom properties for colors and typography
- [ ] Styles for `.rx-*` classes (header, search, filter buttons)
- [ ] Recipe card grid (3 → 2 → 1 columns at breakpoints)
- [ ] Modal overlay and centered content box
- [ ] Hover and active states for buttons
- [ ] Responsive behavior (768px breakpoint)
- [ ] Google Fonts fallback (Georgia for headings, system sans for body)

### Backend (app.js)
- [ ] Load recipes from `<script id="recipes-data">`
- [ ] Wire search input event listener (real-time filtering)
- [ ] Wire filter button event listeners (single-select toggle)
- [ ] Render recipe cards into `.rx-recipe-list`
- [ ] Handle empty state ("No recipes found")
- [ ] Wire card click to open detail modal
- [ ] Populate detail modal on card click (title, metadata, description, ingredients, steps)
- [ ] Handle difficulty and dietary_tags display in detail view (if present in data)
- [ ] Wire modal close (close button and backdrop click)
- [ ] Emoji lookup and injection into `.rx-card-image`

### Writer (recipes JSON)
- [ ] 8 recipes across 3 categories
- [ ] Each recipe: id, name, category, time, servings, description, ingredients, steps
- [ ] Optional: difficulty, dietary_tags
- [ ] Practical, warm voice; short descriptions (1–2 sentences)
- [ ] Short titles (2–4 words)

---

## Quoted agreements from proposals

1. **Frontend proposal:** "Single `index.html` file that opens via double-click. Recipe list view at page load (grid of recipe cards). Clicking a card opens a modal detail view (stays on same page)."
2. **Frontend proposal:** "Responsive meta tag, basic accessibility (alt text patterns, label associations)."
3. **UX proposal:** "3 columns on desktop (≥1024px), 2 columns on tablet (768–1023px), 1 column on mobile (<768px)."
4. **UX proposal:** "Full-screen overlay with semi-transparent backdrop" for the modal.
5. **UX proposal:** "Merriweather (serif, Georgia fallback) — warm, readable, editorial authority. Body/UI: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif."
6. **Writer proposal:** "8 complete recipes across 3 categories (breakfast, main, dessert)."
7. **Backend proposal:** "Data-loading mechanism — frontend will embed a `<script type='application/json' id='recipes-data'>` block in index.html containing the full recipes array."

---

## Decisions made (arbitrations)

### Category filter: single-select (not multi-select)
**Rationale:** This is a small site with 8 recipes. Single-select is simpler to implement, understand, and use. It aligns with frontend's preference for simplicity given the team scope and timeline. Users can still search to narrow results; a radio-button filter is sufficient.

### Modal close: both close button AND backdrop-click
**Rationale:** Close button is explicit and accessible, with 44px minimum touch target (UX standard). Backdrop-click is a common pattern users expect. Both together provide good UX without adding complexity.

### Difficulty & dietary_tags: display in detail modal only (not list cards)
**Rationale:** UX's card design is compact and does not have room for these metadata fields. The detail view has plenty of space. Writer can include them; backend stores and emits them; frontend displays them in the modal. This keeps the list view clean while providing rich detail on demand.

### Field name: `time` (not `time_minutes`)
**Rationale:** Cleaner, shorter field name. The unit (minutes) is implicit from context and the metadata display ("20 min" in the UI).

### Image emoji: hardcoded category map in frontend JS (not per-recipe data field)
**Rationale:** UX designed "one emoji/unicode character per recipe card, placed in `.rx-card-image`. Each category gets a consistent glyph." This suggests a consistent mapping per category, not variation per recipe. Keeping the emoji mapping in frontend JS (not data) avoids bloating the data schema and respects UX's design intent for consistency.

### Empty state: yes, backend implements "No recipes found"
**Rationale:** User feedback when a search returns zero results is important UX. Simple to implement in app.js. Frontend provides the hook (a placeholder div); backend populates it.

### Search: real-time, case-insensitive, substring match, scope = name + description + ingredients
**Rationale:** Modern recipe sites search in real-time. Case-insensitive and substring matching are forgiving and expected. Searching across all three fields gives users power without overwhelming them.

---

## Summary

This spec codifies a single-page, static recipes website with:
- **Data:** 8 recipes in JSON, embedded in HTML, loaded via vanilla JS
- **Structure:** Single index.html, one search input, single-select category filter, recipe grid, modal detail view
- **Styling:** Warm, editorial design (cream cards, burnt orange accent, Merriweather headings) with responsive 3 → 2 → 1 column layout
- **Interactivity:** Real-time search, category filter, modal open/close, no external libraries
- **Compatibility:** Works on file:// protocol (no server), no build step, vanilla HTML/CSS/JS only

All team members now have explicit contracts for their output. The build phase can proceed with confidence.
