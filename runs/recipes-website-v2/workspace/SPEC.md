# Recipes Website — Technical Specification

## Architecture

A vanilla HTML/CSS/JS static site with no build step, no framework, no server. Recipe data is stored in a plain JSON file. Frontend loads data on page load and implements client-side search, filtering, and modal detail views. No external dependencies beyond the browser. The site is fully functional when `src/index.html` is opened in any modern browser.

## File Ownership Table

| Path | Owner | Purpose |
|------|-------|---------|
| `src/index.html` | Frontend | Page structure, semantic HTML markup, initial DOM |
| `src/styles.css` | UX | All styling (colors, typography, layout, responsive behavior) |
| `src/js/main.js` | Frontend | Interactivity: page initialization, modal open/close, event handlers for search/filter |
| `src/js/recipes.js` | Backend | Query utility functions: `getAllRecipes()`, `filterByCategory()`, `search()`, `sortByTime()` |
| `src/data/recipes.json` | Writer | Recipe content (8 recipes, 3 categories, fields per schema) |

**Planning artifacts** (at workspace root, not in src/):
- `SPEC.md` (this file)
- `proposals/` (Phase 1 proposals from all roles)
- `OUTPUT.md` (build/run instructions, written after Phase 3)

## Recipe Data Schema

All recipes are stored in `src/data/recipes.json` as a JSON array. Each recipe object has the following structure:

```json
{
  "id": "string (required, unique identifier, format: 'recipe-NNN', e.g., 'recipe-001')",
  "name": "string (required, recipe title, 2–4 words when possible)",
  "category": "string (required, one of: 'breakfast', 'main', 'dessert')",
  "time": "integer (required, cook time in minutes, e.g., 30)",
  "servings": "integer (required, number of servings, e.g., 4)",
  "description": "string (required, 1–2 sentences, 15–25 words, warm and practical tone)",
  "ingredients": "array<string> (required, each item is a string with amount and ingredient, e.g., '2 cups all-purpose flour')",
  "steps": "array<string> (required, each item is one clear action, e.g., 'Preheat oven to 350°F.')",
  "difficulty": "string (optional, one of: 'easy', 'moderate', 'challenging')",
  "tags": "array<string> (optional, dietary/preference tags, e.g., ['vegetarian', 'gluten-free', 'vegan'])"
}
```

**Example:**

```json
{
  "id": "recipe-001",
  "name": "Fluffy Pancakes",
  "category": "breakfast",
  "time": 20,
  "servings": 2,
  "description": "Light, tender pancakes perfect for a weekend breakfast. Serve with your favorite toppings.",
  "ingredients": [
    "1 1/2 cups all-purpose flour",
    "2 tbsp sugar",
    "2 tsp baking powder",
    "1/2 tsp salt",
    "1 1/4 cups milk",
    "1 egg",
    "2 tbsp melted butter"
  ],
  "steps": [
    "Mix dry ingredients in a large bowl.",
    "Whisk together milk, egg, and melted butter.",
    "Combine wet and dry ingredients until just mixed (lumps are okay).",
    "Heat a griddle or non-stick skillet over medium heat.",
    "Pour 1/4 cup batter per pancake and cook until edges look dry, about 2 minutes.",
    "Flip and cook another 1–2 minutes until golden."
  ],
  "difficulty": "easy",
  "tags": ["vegetarian"]
}
```

**Constraints:**
- `id`: Must be unique and follow the format `recipe-NNN` where NNN is a zero-padded number (e.g., `recipe-001`, `recipe-008`).
- `category`: Must be exactly `'breakfast'`, `'main'`, or `'dessert'` (lowercase, no extra values).
- `name`: Title should be 2–4 words when possible; max 10 words.
- `description`: Must be 1–2 sentences; aim for 15–25 words total. Write in a warm, practical tone (not marketing copy).
- `ingredients`: Array of strings. Each string includes the amount and ingredient name (e.g., `'2 cups flour'`, `'1 tbsp salt'`). No structured objects.
- `steps`: Array of strings. Each string is one clear action. Steps should be detailed enough to be unambiguous.
- `tags`: Optional. Common values are `'vegetarian'`, `'vegan'`, `'gluten-free'`, `'dairy-free'`. No controlled vocabulary; writer chooses.

## CSS Custom Properties (CSS Variables)

Frontend must define these custom properties at the root of `src/styles.css` (or in `src/index.html` `<style>` block). UX will assign values. Every variable listed below must be present for the site to render correctly.

### Color Variables

| Variable Name | Purpose | Type | UX Value |
|---|---|---|---|
| `--color-bg-primary` | Page background | hex color | `#f5f1ed` (cream) |
| `--color-surface` | Card and modal surfaces | hex color | `#ffffff` (white) |
| `--color-text-primary` | Body text and primary content | hex color | `#2a2520` (dark brown) |
| `--color-text-secondary` | Meta text (time, category) | hex color | `#6b6460` (warm gray) |
| `--color-accent` | Links, buttons, accent elements | hex color | `#c1441e` (warm rust) |
| `--color-border` | Card borders, dividers | hex color | `#e8e3de` (light tan) |

### Typography Variables

| Variable Name | Purpose | Type | UX Value |
|---|---|---|---|
| `--font-serif` | Heading font stack | font-family | `Georgia, serif` |
| `--font-sans` | Body and UI font stack | font-family | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` |
| `--font-size-title` | Recipe card/detail title | px | `24px` |
| `--font-size-meta` | Card metadata (time, category) | px | `14px` |
| `--font-size-body` | Body text, descriptions | px | `16px` |
| `--line-height-tight` | Heading line height | unitless | `1.2` |
| `--line-height-normal` | Description and card text | unitless | `1.5` |
| `--line-height-relaxed` | Detail modal body text | unitless | `1.6` |

### Layout & Spacing Variables

| Variable Name | Purpose | Type | UX Value |
|---|---|---|---|
| `--spacing-base` | Base spacing unit | px | `8px` |
| `--card-max-width` | Maximum card width | px | `320px` |
| `--breakpoint-mobile` | Mobile responsive breakpoint | px | `768px` |

**Frontend responsibility:** Define all variables above in `src/styles.css` with initial placeholder values (or UX values). Backend and other roles depend on these variables existing.

**UX responsibility:** Populate the "UX Value" column with actual color codes, font stacks, and measurements in `src/styles.css`.

## Cross-Role Contracts

### BEM CSS Class Names

Frontend must emit exactly these class names in the HTML. UX will style them. No class renames mid-build.

**Recipe list and cards:**
- `.recipe-list` — grid container for recipe cards
- `.recipe-card` — individual recipe card container
- `.recipe-card__title` — recipe name (h2 inside card)
- `.recipe-card__category` — category badge text (e.g., "breakfast")
- `.recipe-card__time` — cook time text (e.g., "30 mins")
- `.recipe-card__description` — recipe description paragraph
- `.recipe-card__action` — "View Recipe" button

**Recipe detail modal:**
- `.recipe-detail-modal` — modal backdrop/container (hidden by default)
- `.recipe-detail-modal__content` — centered content box inside modal
- `.recipe-detail-modal__close` — close button (×)
- `.recipe-detail__title` — recipe name in detail view
- `.recipe-detail__meta` — metadata container (time, servings, category)
- `.recipe-detail__time` — cook time in detail
- `.recipe-detail__servings` — serving size in detail
- `.recipe-detail__category` — category in detail
- `.recipe-detail__description` — description in detail
- `.recipe-detail__ingredients-section` — section wrapper for ingredients
- `.recipe-detail__ingredients-title` — "Ingredients" heading
- `.recipe-detail__ingredients-list` — `<ul>` or `<ol>` containing ingredient items
- `.recipe-detail__ingredient-item` — individual ingredient `<li>`
- `.recipe-detail__steps-section` — section wrapper for steps
- `.recipe-detail__steps-title` — "Instructions" heading
- `.recipe-detail__steps-list` — `<ol>` containing step items
- `.recipe-detail__step-item` — individual step `<li>`
- `.recipe-detail__optional` — wrapper for optional fields (difficulty, tags)
- `.recipe-detail__difficulty` — difficulty level text
- `.recipe-detail__tags` — tag list container
- `.recipe-detail__tag` — individual tag item

**Header and filters:**
- `.app-header` — page header container
- `.search-input` — search input field (also has `id="search-input"`)
- `.category-filter` — category dropdown/select (also has `id="category-filter"`)

### Element IDs and Data Attributes

Frontend must emit these exact IDs and attributes for backend's JavaScript to attach event handlers and read data.

**Recipe cards:**
- Each `.recipe-card` must have `data-recipe-id="recipe-NNN"` (e.g., `data-recipe-id="recipe-001"`)

**Search and filter controls:**
- Search input: `id="search-input"` and `class="search-input"`
- Category dropdown: `id="category-filter"` and `class="category-filter"`
  - Select must contain `<option value="">All Categories</option>` as the first (default) option
  - Then `<option value="breakfast">Breakfast</option>`, `<option value="main">Main</option>`, `<option value="dessert">Dessert</option>`
  - Value must match the category string exactly (lowercase)

**Modal:**
- Recipe detail modal: `class="recipe-detail-modal"` and `hidden` attribute (hidden by default)
- Close button inside modal: `class="recipe-detail-modal__close"`

### JavaScript Function Contracts

Backend's `src/js/recipes.js` module must export these functions. Frontend will call them on user interaction.

```javascript
/**
 * Returns all recipes from the loaded data.
 * @returns {Array<Object>} Array of recipe objects (full schema)
 */
getAllRecipes()

/**
 * Filters recipes by category.
 * @param {Array<Object>} recipes - Array of recipe objects
 * @param {string} category - Category to filter by ('breakfast', 'main', 'dessert')
 * @returns {Array<Object>} Filtered recipe objects
 */
filterByCategory(recipes, category)

/**
 * Searches recipes by text query.
 * Text match is case-insensitive across name, description, and ingredients.
 * @param {Array<Object>} recipes - Array of recipe objects
 * @param {string} query - Search query string
 * @returns {Array<Object>} Matching recipe objects
 */
search(recipes, query)

/**
 * Sorts recipes by cook time (ascending).
 * @param {Array<Object>} recipes - Array of recipe objects
 * @returns {Array<Object>} Sorted recipe objects (lowest time first)
 */
sortByTime(recipes)
```

Frontend flow:
1. On page load, fetch `src/data/recipes.json` and store as a variable (e.g., `allRecipes`)
2. Call `getAllRecipes()` to render the initial list
3. When user types in the search input (event: `input`), call `search(allRecipes, query)` and re-render the list
4. When user selects a category (event: `change`), call `filterByCategory(allRecipes, category)` and re-render the list
5. When user clicks a recipe card, open the detail modal and populate it with the clicked recipe object from the data
6. When user clicks the close button or clicks outside the modal, close the modal

## Content Plan

**Total recipes:** 8

**Distribution by category:**
- **Breakfast:** 3 recipes
- **Main:** 3 recipes
- **Dessert:** 2 recipes

**Per-recipe content:**
- Required fields: name (2–4 words), category, time (minutes), servings, description (1–2 sentences, 15–25 words), ingredients (list of strings), steps (list of strings, one action per step)
- Optional fields: difficulty (easy|moderate|challenging), tags (array of strings like "vegetarian", "gluten-free")

**Tone and voice:** Warm, practical, like a friend who cooks. No flowery marketing copy or overblown adjectives. Focus on why someone would want to make the dish, not why they should.

**Writer's intended recipes:**
1. Fluffy Pancakes (breakfast, easy)
2. Shakshuka (breakfast)
3. Granola with Yogurt (breakfast)
4. Tomato Soup with Grilled Cheese (main)
5. Thai Green Curry with Chicken (main)
6. Baked Salmon with Roasted Vegetables (main)
7. Chocolate Chip Cookies (dessert)
8. Lemon Bars (dessert)

## Data Flow

1. **Content creation:** Writer authors 8 recipes with all required fields (name, category, time, servings, description, ingredients, steps) and optional fields if desired (difficulty, tags). Writer produces content as a JSON array matching the schema in `src/data/recipes.json`.

2. **Data loading:** Frontend's `src/js/main.js` fetches `src/data/recipes.json` on page load using `fetch()`. The JSON is parsed into an array stored in a variable (e.g., `const allRecipes = await response.json()`).

3. **Query logic:** Backend's `src/js/recipes.js` module provides utility functions (`getAllRecipes`, `filterByCategory`, `search`, `sortByTime`). Frontend calls these functions whenever the user interacts with search/filter controls or sorts the list.

4. **Rendering:** Frontend's `src/js/main.js` renders recipe cards based on the returned array. Each card includes a `.recipe-card` element with child elements for title, category, time, description, and action button. All BEM class names and `data-recipe-id` attributes must be present.

5. **Detail modal:** When user clicks a recipe card, frontend opens the detail modal (removes `hidden` attribute), populates the modal with the selected recipe's full data (title, description, ingredients, steps, optional difficulty/tags), and displays the modal to the user. Modal closes on user action (close button or click-outside).

## Content Handoff

**Writer → Backend/Frontend:**

Writer produces `src/data/recipes.json` as a JSON array of recipe objects matching the schema above. The file is plain JSON with no additional processing. Frontend will fetch this file directly using `fetch('src/data/recipes.json')` on page load.

**Writer's deliverable:**
- File: `src/data/recipes.json`
- Format: Valid JSON array of recipe objects
- Content: 8 recipes with all required fields per schema
- Validation: Writer can validate the JSON locally using any JSON validator or by opening the file in a browser's developer console and running `JSON.parse(fileContents)`

**Backend's role:**
- Validates the schema (optional: provides a schema validation script for writer to test against)
- Implements `src/js/recipes.js` query functions that consume the recipes.json data
- The query functions read from the recipes array and return filtered/sorted subsets

**Frontend's role:**
- Fetches `src/data/recipes.json` on page load
- Calls backend query functions on user interaction (search, filter)
- Renders recipe cards and detail modal using the recipe objects
- All rendering uses the class names and attributes specified in the cross-role contracts section

## Modal Detail Contract

The recipe detail modal must have this complete HTML structure. Frontend must emit all classes and elements exactly as specified below:

```html
<div class="recipe-detail-modal" hidden>
  <div class="recipe-detail-modal__content">
    <!-- Close button -->
    <button class="recipe-detail-modal__close">×</button>

    <!-- Recipe title -->
    <h1 class="recipe-detail__title">Recipe Name</h1>

    <!-- Recipe metadata -->
    <div class="recipe-detail__meta">
      <span class="recipe-detail__time">Time: [minutes] mins</span>
      <span class="recipe-detail__servings">Servings: [servings]</span>
      <span class="recipe-detail__category">[category]</span>
    </div>

    <!-- Description -->
    <p class="recipe-detail__description">Recipe description text</p>

    <!-- Ingredients section -->
    <section class="recipe-detail__ingredients-section">
      <h2 class="recipe-detail__ingredients-title">Ingredients</h2>
      <ul class="recipe-detail__ingredients-list">
        <li class="recipe-detail__ingredient-item">ingredient 1</li>
        <li class="recipe-detail__ingredient-item">ingredient 2</li>
        <!-- ... more ingredients -->
      </ul>
    </section>

    <!-- Steps section -->
    <section class="recipe-detail__steps-section">
      <h2 class="recipe-detail__steps-title">Instructions</h2>
      <ol class="recipe-detail__steps-list">
        <li class="recipe-detail__step-item">step 1</li>
        <li class="recipe-detail__step-item">step 2</li>
        <!-- ... more steps -->
      </ol>
    </section>

    <!-- Optional fields (difficulty, tags) -->
    <div class="recipe-detail__optional">
      <!-- Only include if recipe has difficulty -->
      <p class="recipe-detail__difficulty">Difficulty: [easy|moderate|challenging]</p>
      
      <!-- Only include if recipe has tags -->
      <ul class="recipe-detail__tags">
        <li class="recipe-detail__tag">tag1</li>
        <li class="recipe-detail__tag">tag2</li>
        <!-- ... more tags -->
      </ul>
    </div>
  </div>
</div>
```

**Rules:**
- The modal starts with `hidden` attribute
- All class names must match exactly (BEM convention)
- Ingredients section uses `<ul>` (unordered list); steps section uses `<ol>` (ordered list)
- If a recipe lacks optional fields (difficulty, tags), that entire subsection can be omitted
- Modal backdrop (semi-transparent overlay covering the page) is UX's responsibility to style; frontend can apply `::before` or similar to `.recipe-detail-modal` for the backdrop effect

## Category Glyph Implementation

**Decision:** Frontend maintains a hardcoded `categoryGlyphMap` object mapping category names to Unicode glyphs. Glyphs are inserted by frontend during rendering of recipe cards and detail views.

**Implementation:**

Frontend defines a constant in `src/js/main.js`:

```javascript
const categoryGlyphMap = {
  'breakfast': '🍳',
  'main': '🍽️',
  'dessert': '🍰'
};
```

When rendering a recipe card or detail view, frontend inserts the glyph before the category text:

```javascript
// Example: rendering a card
const categorySpan = document.createElement('span');
categorySpan.className = 'recipe-card__category';
const glyph = categoryGlyphMap[recipe.category];
categorySpan.textContent = `${glyph} ${recipe.category}`;
```

**UX responsibility:** UX may style the glyph within `.recipe-card__category` and `.recipe-detail__category` (e.g., adjust sizing, color, spacing), but the glyph content itself is controlled by frontend's hardcoded map. UX cannot change glyph characters without frontend changing the map.

**Writer responsibility:** Writer does NOT include glyphs in recipe content. Glyphs are purely a rendering concern for frontend.

**Backend responsibility:** Backend's query functions do not interact with glyphs.

## Summary

This specification locks all cross-role contracts. Every teammate has the exact names, paths, functions, and content structure they need to build their slice without further negotiation.

- **Frontend** produces `src/index.html`, `src/js/main.js` with all required class names and event handlers
- **UX** produces `src/styles.css` with all color, typography, and layout rules; populates CSS variables
- **Backend** produces `src/js/recipes.js` with query functions; validates `src/data/recipes.json` schema
- **Writer** produces `src/data/recipes.json` with 8 recipes matching the schema

All four roles can build in parallel (Phase 3) without further cross-team messages.
