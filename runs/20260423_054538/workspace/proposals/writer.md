# Proposal — Writer

## My slice

I will produce **8 recipes** across **3 categories** (breakfast, main, dessert), written in a warm, practical cook's voice.

**Recipe list (intended):**

### Breakfast (3 recipes)
1. Fluffy Pancakes
2. Shakshuka
3. Granola with Yogurt

### Main (3 recipes)
4. Tomato Soup with Grilled Cheese
5. Thai Green Curry with Chicken
6. Baked Salmon with Roasted Vegetables

### Dessert (2 recipes)
7. Chocolate Chip Cookies
8. Lemon Bars

**Per-recipe content:**
- Name, category, time (minutes), servings
- Description: 1–2 sentences max, warm and practical (not marketing copy)
- Ingredients: list of strings with amounts (e.g., "2 cups all-purpose flour")
- Steps: ordered list, one action per step, clear and unambiguous
- Optional fields: difficulty (easy / moderate / challenging), dietary tags (vegetarian, vegan, gluten-free)

**Voice & tone:**
- Write like a friend who has actually made the dish.
- Focus on why someone would want to cook it, not why they should want to.
- Short, direct language. No flowery adjectives or "embark on a culinary journey" nonsense.
- Descriptions fit a recipe card (title + one line of metadata + description should scan in 2 seconds).

**Content density:**
- Titles: 2–4 words when possible.
- Descriptions: 1–2 punchy sentences, roughly 15–25 words.
- Steps: as detailed as needed to be clear; brevity doesn't override clarity.

## What I need from others

### From backend
- **Confirm the schema covers these fields:** name (string), category (string), time (integer), servings (integer), description (string), ingredients (list of strings), steps (list of strings).
- **Confirm ingredients shape:** I prefer strings-with-amounts ("2 cups flour") over structured objects. Is that compatible with your data layer? If you need a different shape, tell me now.
- **Optional fields:** I'd like to offer difficulty and dietary tags, but I don't need them if they complicate your schema.

### From UX
- **Confirm card density:** My descriptions are 1–2 sentences, titles 2–4 words. Will those fit the recipe card container you're designing? Or do you need me to adjust?
- **Confirm image approach:** Are we going no images, or unicode glyphs per category? Affects whether the description needs to carry more visual weight.

### From frontend
- **No blocking needs, but:** I'm curious what view technology you'll choose (static HTML, React, Vue, etc.) because it shapes backend's data handoff to you. Doesn't affect my content, just nice to know the context.

## Open decisions for the team

1. **Recipe count:** I'm proposing 8 to show variety without making the site feel thin if development runs short. The team can push back to 6 or up to 10, but 8 feels right for an afternoon's work.

2. **Ingredient data shape:** My preference is strings-with-amounts, but if backend's chosen stack wants structured objects (quantity + unit + ingredient name), I'll write the content to fit. Needs to be decided in Phase 2.

3. **Dietary tags — nice-to-have or must-have?** I can add vegetarian/vegan/gluten-free tags to every recipe, but it's polish, not essential. Let backend call this based on complexity.

4. **Image handling:** UX mentioned either no images or unicode glyphs. Both work with my content. Awaiting UX's final pick so I know whether to plan extra description weight for visual balance.
