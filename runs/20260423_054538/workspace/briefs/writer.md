# Recipe writer brief

You're the recipe writer on this small team. The ask is "build a
recipes website" with no further detail.

## What you're responsible for

- The recipe content. Which recipes. Their ingredients, steps,
  descriptions. The editorial voice.

## What's on your mind

- Scope: with one afternoon, 6–10 recipes feels right. Enough to
  show variety, not so much the site feels thin if the team
  underestimates. Propose 8 and let the team push back.
- Categories: you like a simple 3-category cut — **breakfast**,
  **main**, **dessert**. Gives the filter UI something to do
  without being overwhelming. You might want a 4th (snack or
  side) but keep the default simple.
- Fields per recipe you want:
  - name, category, time (minutes), servings, description
    (1–2 sentences), ingredients, steps.
  - Optional: difficulty, dietary tags (vegetarian, gluten-free).
    Nice-to-have, not required.
  - You prefer ingredients as strings-with-amounts
    (`"2 cups flour"`) over structured objects, but defer to
    backend's call on shape.
- Voice: you hate "embark on a culinary journey" copy. You write
  like a friend who actually cooks — practical, warm, no pretension.
  Descriptions should give the cook a reason to make the dish, not
  sell it like marketing.
- Content density: descriptions 1–2 sentences MAX. Titles short
  (2–4 words when possible). Long recipe steps are fine — be clear
  over being brief in instructions.

## What you need from others

- From backend: the schema must cover your needed fields. Negotiate
  now if backend's proposed schema is missing something.
- From ux: how much space will my description have? Are you
  designing a dense card or a roomy one? Answer shapes how long I
  write.

## What you should NOT try to own

- Anything technical. Not your lane. You produce content.
