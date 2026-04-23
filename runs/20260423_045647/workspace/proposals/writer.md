# Proposal — Recipe Writer

## My slice

I will write **8 complete recipes** across **3 categories** (breakfast, main, dessert) with the following content per recipe:

- **Name** — short titles, 2–4 words (e.g., "Fluffy Pancakes", "Grilled Salmon", "Chocolate Lava Cake")
- **Category** — breakfast | main | dessert
- **Time** — cooking time in minutes (integer)
- **Servings** — integer
- **Description** — 1–2 sentences, warm and practical voice. Why you'd make this dish, not marketing fluff.
- **Ingredients** — ordered array of strings formatted as "amount unit ingredient" (e.g., "2 cups flour", "1 can chickpeas")
- **Steps** — ordered array of instruction strings, clear and conversational

Recipe list (proposed):

**Breakfast (3)**
- Fluffy Pancakes
- Avocado Toast
- Shakshuka

**Main (3)**
- Grilled Salmon
- Pasta Carbonara
- Chicken Stir-Fry

**Dessert (2)**
- Chocolate Lava Cake
- Lemon Bars

## What I need from others (contracts)

**From backend:**
- Confirm the data schema will support: name, category, time, servings, description, ingredients (array), steps (array).
- Optionally: difficulty (easy/medium/hard), dietary_tags (vegetarian, vegan, gluten_free, etc.). These are nice-to-have; I can work without them if the schema doesn't support.
- Confirm the format for ingredients strings (e.g., "2 cups flour" vs. structured object). I assume flat strings per the brief.

**From UX:**
- Confirm card design is punchy and compact: short titles (2–4 words) will fit cleanly, descriptions (1–2 sentences) sit on 1–2 lines without forcing tall cards.
- Confirm you're using emoji/unicode glyphs per category (e.g., 🍳 breakfast, 🍽️ main, 🍰 dessert) so I know the visual style. I won't embed emoji in my recipe text.

**From frontend:**
- No direct needs; backend and UX class contracts will shape how my content flows.

## Open decisions for the team

1. **Difficulty and dietary tags**: Should I include optional fields in each recipe (difficulty: easy/medium/hard, dietary_tags: ["vegetarian"], etc.)? I can write these, but backend needs to commit to the schema fields, and UX needs to decide if cards have space to display them.
   - *Preferred: include difficulty for all recipes and dietary_tags where relevant (vegetarian, vegan, gluten-free). Adds useful filterable metadata without cluttering the proposal.*

2. **Recipe diversity**: The 8 recipes span global styles (Mediterranean salmon, Italian carbonara, Asian stir-fry, Middle Eastern shakshuka, American pancakes). Should I stay international or narrow to a specific cuisine?
   - *Preferred: stay international. Shows recipe breadth, tests the site's versatility, and most home cooks want variety.*

3. **Cooking difficulty**: Should all 8 recipes be accessible (weeknight-friendly, 30-60 min cook time) or include one or two more ambitious dishes?
   - *Preferred: stick to accessible weeknight recipes. The site should encourage cooking, not intimidate.*
