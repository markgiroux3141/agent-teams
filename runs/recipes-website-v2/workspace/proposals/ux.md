# UX Proposal

## My slice

A warm, editorial visual direction — cookbook-inspired, not SaaS-clean. The design prioritizes legibility and a personal, inviting feel over minimal-flat aesthetics.

**Color palette:**
| Token | Hex | Role |
|-------|-----|------|
| `color-bg-primary` | `#f5f1ed` | Page background (cream/off-white) |
| `color-surface` | `#ffffff` | Card and modal surfaces |
| `color-text-primary` | `#2a2520` | Body text and primary content |
| `color-text-secondary` | `#6b6460` | Meta text (time, category) |
| `color-accent` | `#c1441e` | Links, buttons, category badges (warm rust) |
| `color-border` | `#e8e3de` | Card borders and dividers |

**Typography:**
- **Headings (h1–h3):** Georgia (serif, system fallback: `Georgia, serif`) — warm, traditional, readable at scale
- **Body text:** System sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`) — clean, accessible
- **Type scale:** 
  - Recipe title: 24px / 1.2 line-height
  - Card meta (time, category): 14px / 1.4
  - Card description: 16px / 1.5
  - Body text in detail modal: 16px / 1.6

**Layout & Responsive:**
- **Recipe list:** CSS Grid, auto-fit columns, 2–3 columns on desktop (each card max-width 320px), collapse to 1 column at 768px breakpoint
- **Card structure:** Padding 20px, minimum touch target 44px height for interactive elements
- **Spacing scale:** 8px base unit (8, 16, 24, 32px used throughout)

**Visual hierarchy:**
- Recipe title: bold, serif, 24px
- Category badge: accent color, sans-serif, 14px
- Cook time: secondary text, sans-serif, 14px
- Description: body sans-serif, 16px, leading 1.5

**Category marker:** Unicode glyph per category (e.g., 🍝 Pasta, 🥗 Salad, 🍰 Dessert) — placed inline with category name, no external images.

**Details view:** Modal overlay (semi-transparent backdrop), centered card with recipe title, ingredients, steps. Same color palette and typography rules apply.

## What I need from others (contracts)

**From frontend:**
- BEM-style CSS class names as discussed:
  - `.recipe-list` — grid container
  - `.recipe-card`, `.recipe-card__title`, `.recipe-card__time`, `.recipe-card__category`, `.recipe-card__description` — card components
  - `.recipe-detail-modal` — modal overlay and content container
  - `.category-filter`, `.search-input` — filter/search UI
  - `.app-header` — page header
- Confirm these class names will be present in the HTML I'm styling against. I'll write CSS targeting these names exactly; no class renamings mid-build.

**From writer:**
- Descriptions as 1–2 punchy sentences (15–25 words max). This fits the card padding and line-height I'm designing.
- Confirmation of final category count and names (so I can design category badge styling and glyph pairing if needed).

**From backend:**
- No immediate dependency. You'll write SPEC.md with data schema; I'll integrate once SPEC is locked.

## Open decisions for the team

1. **Accent color preference:** I'm proposing a warm rust (`#c1441e`). Team consensus okay with this, or prefer mustard yellow (`#d4a574`) or deep green (`#3d5a42`)? 
   - *My reasoning:* Rust reads warm and inviting without being jarring. Complements cream background and pairs well with dark text.

2. **Serif font for headings:** I'm proposing Georgia (system stack, no external font load). Safer for a demo site than Google Fonts; Georgia renders well at scale and feels editorial. Acceptable, or should we import a web font (e.g., Playfair Display, Merriweather)?
   - *My reasoning:* System stack minimizes external dependencies. Georgia is installed on ~99% of machines.

3. **Card aspect ratio:** No fixed aspect ratio; cards will expand vertically based on description length. Acceptable for a punchy 1–2 sentence description?
   - *My reasoning:* Flexible height lets the description breathe without artificial truncation.
