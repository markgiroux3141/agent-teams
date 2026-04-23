# UX Proposal — Recipes Website

## My slice

I'm proposing a **warm, editorial, card-based design** that feels like a favorite cookbook, not a SaaS dashboard.

### Design direction

**Mood:** Approachable, handcrafted, timeless. The site should feel like the owner cares about food and the presentation — think a well-designed cookbook or a food blog with real taste.

**Color palette:**

| Token | Role | Value | Usage |
|-------|------|-------|-------|
| `--rx-bg` | Page background | `#FAF7F2` (warm off-white) | Body, page container |
| `--rx-surface` | Card surface | `#FFFBF7` (soft cream) | Card backgrounds, elevated surfaces |
| `--rx-text-primary` | Body text | `#2B2520` (dark brown) | Headings, recipe titles, body copy |
| `--rx-text-secondary` | Metadata | `#6B6459` (muted brown) | Time, yield, category labels |
| `--rx-accent` | Interactive, highlights | `#C85A17` (burnt orange) | Links, hover states, category badges |
| `--rx-border` | Soft dividers | `#E8E3DC` (warm gray) | Card borders, subtle rules |

### Typography

- **Headings:** Merriweather (serif, Georgia fallback) — warm, readable, editorial authority.
  - Google Fonts link: `https://fonts.googleapis.com/css2?family=Merriweather:wght@700&display=swap`
- **Body/UI:** -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif — clean, modern, accessible.
- **Line height:** 1.6 on body text (generous, readable).
- **Font sizes:** 
  - Recipe title (`.rx-card-title`): 1.5rem / 24px, serif, dark brown
  - Card metadata (`.rx-card-meta`, `.rx-card-time`, `.rx-card-category`): 0.875rem / 14px, secondary text color
  - Description (`.rx-card-description`): 1rem / 16px, body text, line-height 1.5

### Layout

**List view:**
- **Grid:** 3 columns on desktop (≥1024px), 2 columns on tablet (768–1023px), 1 column on mobile (<768px).
- **Card anatomy (`.rx-card`):**
  - Category emoji/glyph (`.rx-card-image`) — single emoji character, sized prominently for visual anchor
  - Recipe title (`.rx-card-title`) — short, 2–4 words max (e.g., "Fluffy Pancakes")
  - Metadata (`.rx-card-meta`): time, yield, category as small labels
  - Description (`.rx-card-description`) — 1–2 punchy sentences (e.g., "Crispy edges, fluffy center, ready in 20 minutes.")
- **Card spacing:** 20px padding inside cards, 20px gap between cards. Roomy, not cramped.
- **Card dimensions (design intent):** ~280–320px wide, height flexible (~200–240px typical).
- **Hover state:** Subtle shadow lift or border accent on hover to signal interactivity.

**Responsive behavior:**
- At ≥1024px: 3-column grid
- At 768–1023px: 2-column grid
- Below 768px: single column, full width with 16px side margins
- Touch targets: minimum 44×44px for interactive elements (e.g., modal close button)

**Page-level:**
- Header (`.rx-header`) with logo/title
- Search input (`.rx-search-input`) and filter buttons (`.rx-filter-button`) if included
- Recipe grid container (`.rx-recipe-list`)
- Page container: max-width ~1200px, centered, 24px margins on desktop, 16px on mobile

**Detail view (modal):**
- Modal overlay (`.rx-detail-modal`) — full-screen overlay with semi-transparent backdrop
- Inside modal: ingredients list (`.rx-ingredients-list`), steps list (`.rx-steps-list`)
- Close affordance: intuitive, touch-friendly (e.g., button, X in corner)

### Image strategy

**Confirmed:** One emoji/unicode character per recipe card, placed in `.rx-card-image`. Each category gets a consistent glyph (e.g., 🍳 for breakfast, 🍽️ for main, 🍰 for dessert). This is lightweight, no external URLs, adds visual warmth without cuteness.

---

## What I need from others (contracts)

### From frontend — LOCKED IN ✓

I will style these CSS classes:

**Page-level:**
- `.rx-header`
- `.rx-search-input`
- `.rx-filter-button`

**List view:**
- `.rx-recipe-list` (grid container)
- `.rx-card` (individual recipe card)
- `.rx-card-image` (emoji/glyph placeholder, single character)
- `.rx-card-title` (recipe name)
- `.rx-card-description` (1–2 sentence description)
- `.rx-card-meta` (time, yield, category metadata)
- `.rx-card-time`
- `.rx-card-category`

**Detail view (modal):**
- `.rx-detail-modal` (modal container/overlay)
- `.rx-ingredients-list`
- `.rx-steps-list`

**Frontend commits to:** Emitting all these classes in your HTML. I won't style by tag selectors, only by class. `.rx-card-image` should be a single character wide — I'll style it to hold the emoji glyph.

**Google Fonts:** Frontend will add this `<link>` to `<head>`:
```html
<link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@700&display=swap" rel="stylesheet">
```

### From writer — LOCKED IN ✓

**Content plan:**
- **Titles:** SHORT — 2–4 words max (e.g., "Fluffy Pancakes", "Grilled Salmon", "Chocolate Lava Cake").
- **Descriptions:** ONE punchy sentence, maybe two if the first is brief. Practical tone: why you'd make it, no marketing fluff.
- **Images:** Emoji glyphs per category (no emoji embedded in description text; frontend handles glyph placement in `.rx-card-image`).

**Writer commits to:** Keeping descriptions punchy and short so they fit 1–2 lines on a ~280–320px wide card. I'm designing roomy spacing; descriptions will have breathing room.

### From backend

1. **Data structure:** Each recipe object should include:
   - `title` (string, 2–4 words)
   - `description` (string, 1–2 sentences)
   - `time` or `duration` (for "15 min" metadata)
   - `category` (string, for emoji mapping: "breakfast", "main", "dessert", etc.)
2. **Search/filter scope:** Frontend's message mentions `rx-filter-button`, so filters are in scope. I'll style those buttons; backend handles the logic.

---

## Open decisions for the team

### 1. Tablet column count — RESOLVED
**Decision:** 2 columns at 768–1023px. Writer's short content and roomy spacing make this work well; text measure stays readable.

### 2. Accent color tone — PROPOSED
**My choice:** Burnt orange (`#C85A17`) — warm, food-forward, earthy. Feels like spices and clay, not SaaS.

**Alternatives if team disagrees:**
- Deep mustard (`#D4A574`) — warmer, earthier
- Sage green (`#7B9D83`) — cooler, more modern
- Warm red (`#B84D3A`) — slightly more classic

**Any objections?**

### 3. Detail view modal depth
**My proposal:** Full-screen modal overlay with semi-transparent backdrop. Click card → modal appears. Escape or close button dismisses it.

**Assumption:** Frontend's single-page design (no separate recipe.html) works well for this. No page reload needed.

---

## Deliverables

1. **Design tokens (above):** Color palette + typography specs.
2. **`styles.css`:** Plain CSS, no frameworks. Styles all `rx-*` classes for list view, detail view, and page header. Includes media query at 768px for responsive collapse.
3. **Responsive behavior:** 3 → 2 → 1 column at breakpoints. Touch-friendly spacing.
4. **Google Fonts link:** Frontend adds to `<head>`.

---

## Notes

- **No CSS frameworks** — vanilla CSS with custom properties (`--rx-bg`, `--rx-text-primary`, etc.).
- **No build step.** Plain CSS, zero dependencies.
- **Offline-compatible:** Google Fonts only external resource; can be replaced with system fonts if needed.
- **Single-page app:** I'm styling for list view + modal detail view. Frontend handles routing/modal logic.
- **Images:** Only emoji glyphs; no external image URLs or binary assets.
