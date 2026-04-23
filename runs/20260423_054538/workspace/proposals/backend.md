# Backend Proposal

## My slice

I'll build the data layer for a vanilla HTML/CSS/JS static site. This includes:

1. **Recipe data schema** (JSON structure)
   - A single `recipes.json` file at `src/data/recipes.json`
   - Array of recipe objects with fields: `id`, `name`, `category`, `time`, `servings`, `description`, `ingredients`, `steps`, plus optional `difficulty` and `tags`
   - No server; data is plain JSON frontend fetches on page load

2. **Client-side query logic** (JavaScript module)
   - A `src/js/recipes.js` module that provides:
     - `getAllRecipes()` — returns all recipes
     - `filterByCategory(category)` — filters by breakfast|main|dessert
     - `search(query)` — text search across name, description, ingredients
     - `sortBy(field, direction)` — sort by time, servings, name, difficulty
   - These functions consume the recipes.json data and return filtered/sorted arrays
   - No external dependencies — vanilla JS only

3. **Schema validation** (optional, but included)
   - A light validator to ensure recipe objects conform to schema during development
   - Not used at runtime, just for content integrity

## What I need from others

**From writer** (confirmed):
- Recipes in a JSON format matching the schema below, saved as `src/data/recipes.json`
- Content for 8 recipes across breakfast/main/dessert (and optionally snack)
- Ingredients as strings with amounts (e.g., "2 cups flour" — no structured objects)

**From frontend** (confirmed):
- Call `getAllRecipes()` on page load and render the recipe list
- On filter/category click, call `filterByCategory()` and re-render
- On search input, call `search()` and re-render
- On detail-modal trigger, pass the recipe ID and render full details from the recipe object
- Confirm you'll fetch `src/data/recipes.json` on page load (or I can pre-bundle it as recipes.js if you prefer)

**From ux** (minor clarification):
- Confirm: no external images in the design, icons/glyphs handled entirely in CSS? (affects whether I store any image/emoji field in schema)
- Given that, the schema I'm proposing does NOT include image/icon fields — ux owns that styling

## Recipe data schema

```json
{
  "id": "string (unique, e.g., 'recipe-001')",
  "name": "string (required, e.g., 'Scrambled Eggs')",
  "category": "string (required, enum: 'breakfast' | 'main' | 'dessert' | 'snack')",
  "time": "integer (required, minutes, e.g., 15)",
  "servings": "integer (required, e.g., 2)",
  "description": "string (required, 1–2 sentences, e.g., 'Soft, fluffy scrambled eggs with a hint of cream.')",
  "ingredients": "array<string> (required, e.g., ['3 eggs', '1 tbsp butter', 'salt to taste'])",
  "steps": "array<string> (required, e.g., ['Whisk eggs in a bowl...', 'Heat butter in pan...'])",
  "difficulty": "string (optional, enum: 'easy' | 'moderate' | 'challenging')",
  "tags": "array<string> (optional, e.g., ['vegetarian', 'gluten-free', 'vegan'])"
}
```

**Example recipe object:**

```json
{
  "id": "recipe-001",
  "name": "Scrambled Eggs",
  "category": "breakfast",
  "time": 10,
  "servings": 2,
  "description": "Soft and fluffy scrambled eggs with just a touch of cream.",
  "ingredients": ["3 eggs", "1 tbsp butter", "2 tbsp heavy cream", "salt and pepper to taste"],
  "steps": [
    "Whisk eggs and cream together in a small bowl.",
    "Heat butter in a non-stick skillet over medium heat.",
    "Pour in eggs and stir constantly until just set, about 2–3 minutes.",
    "Season with salt and pepper. Serve immediately."
  ],
  "difficulty": "easy",
  "tags": ["vegetarian", "gluten-free"]
}
```

## Open decisions for the team

1. **Snack category** — Writer's brief suggests 3 base categories (breakfast, main, dessert) but mentions a possible 4th (snack or side). Decision: **propose 3 base, add snack if writer has content for it**. No schema change needed; just update the category enum.

2. **Image/icon handling** — UX mentioned either no images or unicode/icon glyphs per category as a marker. My schema does NOT include any image or icon field; I'm assuming icons are purely CSS-based (e.g., `data-category="breakfast"` CSS selector targets an ::before pseudo-element). **Confirm with UX** that this works. If not, I'll add an optional `icon` or `emoji` field.

3. **Module vs import** — Frontend confirmed recipes.json works, but frontend can also request recipes.js as a CommonJS/ES6 module if they prefer import over fetch. Current plan: recipes.json for simplicity. Easy to change if frontend needs otherwise.

## Architecture summary

**Data source**: `src/data/recipes.json` (writer owns)  
**Query logic**: `src/js/recipes.js` module with filter/search/sort functions (backend owns)  
**Consumer**: Frontend's view code fetches recipes.json on load, calls query functions on interaction  
**No server, no build step, no external dependencies.** Simplest possible data plane for the scope.
