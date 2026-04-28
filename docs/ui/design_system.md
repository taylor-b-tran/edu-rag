# Paedia Visual Design Guidelines

**Design System v1.1**
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)
Date: April 2026

---

## 1. Design Principles

These five principles guide every design decision in Paedia:

1. **Clarity over decoration** — The interface serves learning. Every element must have a clear purpose. Remove anything that doesn't help the student find answers.
2. **Familiar patterns** — Use established UI conventions (chat bubbles, card layouts, sidebar navigation) so students can focus on content, not learning the interface.
3. **Trust through transparency** — Always show source citations and confidence levels. Students need to know where answers come from. When no relevant chunks are found, the fallback label "Based on general knowledge — not verified against course materials" is shown.
4. **Accessible by default** — Sufficient contrast ratios, readable font sizes, and keyboard-navigable components.
5. **Responsive and fast** — The UI should feel instant. Loading states and skeleton screens prevent perceived lag.

---

## 2. Branding Identity

| Element | Value |
|---------|-------|
| Group name | Aletheia's Zetetes |
| Product name | Paedia |
| Project name | EduRAG |
| Identity style | Academic and professional presentation with the existing group logo and a simple product name |
| Tone | Professional, educational, and technically grounded |

The branding approach is lightweight but consistent. The same group name, product name, colour treatment, and figure styling carry over into Sprint 4 presentation assets and the prototype UI.

For exported wireframes, use the Assessment 2 logo mark asset at `docs/assets/paedia_logo_mark.png` instead of an emoji glyph. This avoids missing-font boxes in PNG exports and keeps the wireframes aligned with the report branding.

---

## 3. Colour Palette

### Primary Colours (Navy / Teal / Gold)

| Name | Hex | Usage |
|------|-----|-------|
| Navy 700 (Primary) | `#1B2A4A` | Major headings, sidebar background, primary text |
| Navy 900 | `#0F1B33` | Deepest emphasis, header bar background |
| Navy 50 | `#E8ECF4` | Active nav backgrounds, light highlights |
| Teal 600 (Secondary) | `#0D9488` | Secondary actions, links, active navigation, user avatars |
| Teal 800 | `#0A7A6F` | Hover states, gradient endpoints |
| Teal 50 | `#E6F7F5` | Active nav pill backgrounds, light teal highlights |
| Gold 500 (Tertiary) | `#D4A843` | Tertiary emphasis, badges, accent highlights |
| Gold 700 | `#B8922E` | Hover state for gold accents |
| Gold 50 | `#FDF6E3` | Gold badge backgrounds, subtle warm highlights |

### Neutral Colours

| Name | Hex | Usage |
|------|-----|-------|
| Gray 900 | `#1A1A2E` | Headings, primary text |
| Gray 700 | `#5F6368` | Body text, secondary labels |
| Gray 400 | `#9AA0A6` | Captions, timestamps, placeholders |
| Gray 200 | `#E8EAED` | Borders, dividers, card outlines |
| Gray 50 | `#F8F9FA` | Page background |
| White | `#FFFFFF` | Cards, panels, content area |

### Semantic Colours

| Name | Hex | Usage |
|------|-----|-------|
| Green 600 | `#34A853` | Success, "Indexed" status, high confidence |
| Green 50 | `#E6F4EA` | Success badge background |
| Yellow 600 | `#F9AB00` | Warning, "Processing" status, medium confidence |
| Yellow 50 | `#FEF7E0` | Warning badge background |
| Red 600 | `#EA4335` | Error, "Failed" status, delete actions |
| Red 50 | `#FCE8E6` | Error badge background |

### Usage Rules

- Never use more than 2 semantic colours on the same card or component.
- Navy is used for structural elements (headings, sidebar, header). Teal is reserved for interactive elements (buttons, links, active states). Gold is reserved for accent highlights and tertiary emphasis.
- Text on coloured backgrounds must meet WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text).
- The fallback label uses Yellow 600 background to visually distinguish ungrounded responses.

---

## 4. Typography

### Font Stack

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

Inter is chosen for its excellent readability at small sizes and clean aesthetic. The fallback stack ensures consistent rendering across platforms.

### Type Scale

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Display | 24px | 700 | 1.3 | Page titles ("Ask your course materials") |
| Heading | 18px | 700 | 1.4 | Section headers, card titles |
| Subheading | 16px | 600 | 1.4 | Nav items (active), emphasis |
| Body | 14–15px | 400 | 1.6 | Chat messages, descriptions, table content |
| Caption | 12px | 400 | 1.4 | Timestamps, metadata, source labels |
| Tiny | 11px | 400 | 1.3 | Status bar, wireframe labels |

### Rules

- Body text should never be smaller than 14px.
- Headings use `font-weight: 700` in Navy 700, subheadings use `600`, body uses `400`.
- Line height for body text is 1.6 for readability in dense answer content.
- Limit to 2–3 type sizes per screen to maintain visual hierarchy.

---

## 5. Spacing System

Paedia uses a 4px base grid for consistent spacing.

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | Inline spacing, icon gaps |
| `sm` | 8px | Tight padding, chip margins |
| `md` | 16px | Card padding, section gaps |
| `lg` | 24px | Between major sections |
| `xl` | 32px | Page margins, hero spacing |
| `2xl` | 48px | Between screen regions |

### Rules

- Card internal padding: `16px–24px`.
- Sidebar width: `260px` (fixed).
- Chat message max-width: `80%` (user), `85%` (AI).
- Minimum touch target size: `44px × 44px`.

---

## 6. Component Library

### 6.1 Buttons

| Variant | Background | Text | Border | Usage |
|---------|-----------|------|--------|-------|
| Primary | `#0D9488` (Teal 600) | White | None | Main CTA: "Sign In", "Upload & Index" |
| Secondary | White | `#5F6368` | `#E8EAED` | Alternative actions: "Export CSV", "Cancel" |
| Danger | White | `#EA4335` | None | Destructive: "Delete" |
| Ghost | Transparent | `#0D9488` | None | Inline actions: "Continue", "Edit" |
| Accent | `#D4A843` (Gold 500) | White | None | Highlight actions, promotional CTA |

All buttons use `border-radius: 8px`, `padding: 10px 20px`, `font-weight: 500`.

### 6.2 Input Fields

- Border radius: `24px` (chat input), `6px` (form fields)
- Border: `1px solid #E8EAED`
- Focus state: `border-color: #0D9488` + `box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15)`
- Placeholder colour: `#9AA0A6`

### 6.3 Cards

- Background: `#FFFFFF`
- Border: `1px solid #E8EAED`
- Border radius: `10px–12px`
- Shadow: `0 1px 3px rgba(0, 0, 0, 0.04)` (resting), `0 2px 8px rgba(0, 0, 0, 0.08)` (hover)
- Padding: `16px–24px`

### 6.4 Chat Bubbles

**User messages:**
- Background: `linear-gradient(135deg, #0D9488, #0A7A6F)`
- Text: White
- Border radius: `18px 18px 4px 18px` (tail bottom-right)
- Shadow: `0 2px 8px rgba(13, 148, 136, 0.2)`

**AI messages:**
- Background: `#FFFFFF`
- Text: `#1A1A2E`
- Border: `1px solid #E8EAED`
- Border radius: `18px 18px 18px 4px` (tail bottom-left)
- Includes source chips and confidence bar

**Fallback AI messages:**
- Background: `#FFFFFF`
- Border: `1px solid #F9AB00` (Yellow 600 border to signal ungrounded response)
- Prepended label: "Based on general knowledge — not verified against course materials"

### 6.5 Status Badges

- Border radius: `12px`
- Padding: `3px 12px`
- Font: `11px`, `font-weight: 600`
- Variants: Indexed (green), Processing (yellow), Failed (red), Pending (gray)

### 6.6 Source Citation Chips

- Background: `#F1F3F4`
- Border: `1px solid #E8EAED`
- Border radius: `16px`
- Padding: `4px 14px`
- Hover: background shifts to `#E6F7F5`, border to `#0D9488`
- Displays: filename, page number, similarity score

### 6.7 Navigation Items

- Height: `38px`
- Border radius: `6px`
- Active: `background: #E6F7F5`, `color: #0D9488`, `font-weight: 600`
- Inactive: `color: #5F6368`, `font-weight: 400`
- Icon + text separated by `8px`

### 6.8 Confidence Bar

- Height: `6px`
- Border radius: `3px`
- Background track: `#E8EAED`
- Fill ≥ 0.8: `#34A853` (Green 600)
- Fill 0.5–0.79: `#D4A843` (Gold 500)
- Fill < 0.5: `#EA4335` (Red 600)
- Fill width animates over 800ms with `ease` easing

---

## 7. Layout Grid

### Desktop (≥ 1200px)

```
┌──────────┬──────────────────────────────────────┐
│          │                                      │
│ Sidebar  │          Main Content                │
│  260px   │          (fluid)                     │
│ Navy 900 │                                      │
│          │                                      │
│          │                                      │
│          │                                      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

### Tablet (768–1199px)

- Sidebar collapses to icon-only (56px width)
- Main content expands to fill

### Mobile (< 768px)

- Sidebar becomes a slide-over drawer
- Chat input pinned to bottom
- Cards stack vertically

---

## 8. Iconography

Paedia uses the Assessment 2 logo mark for brand placement. Other simple emoji icons can remain in the prototype phase due to Streamlit's native support, but exported wireframes should avoid emoji for the main logo because it can render as a missing-font box.

| Icon | Meaning |
|------|---------|
| `docs/assets/paedia_logo_mark.png` | Paedia logo / brand mark |
| 💬 | Q&A Chat |
| 📋 | Session History |
| 📁 | Documents / Uploads |
| ⚙️ | Admin / Settings |
| 📄 | Individual document |
| 🔍 | Search |
| ➤ | Send message |

For the React stretch goal, migrate to [Lucide React](https://lucide.dev/) icons for a consistent, scalable icon system.

---

## 9. Motion & Transitions

| Element | Property | Duration | Easing |
|---------|----------|----------|--------|
| Button hover | background, shadow | 200ms | ease |
| Card hover | box-shadow | 200ms | ease |
| Source chip hover | background, border | 200ms | ease |
| Confidence bar fill | width | 800ms | ease |
| Page transition | opacity | 150ms | ease-in-out |

Keep animations subtle and functional. No decorative animations that could distract from learning.

---

## 10. Accessibility

- **Colour contrast**: All text meets WCAG AA (4.5:1 for normal text). Navy 700 on white = 10.5:1. Teal 600 on white = 4.6:1.
- **Focus indicators**: All interactive elements show a visible focus ring (2px teal outline).
- **Keyboard navigation**: Tab order follows visual order. Enter/Space activates buttons.
- **Screen readers**: Semantic HTML elements (headings, lists, buttons) are used throughout.
- **Reduced motion**: Respect `prefers-reduced-motion` media query — disable transitions when set.

---

## 11. React Migration Notes

When migrating to React, the design system translates as follows:

| Streamlit | React |
|-----------|-------|
| Custom CSS in `st.markdown` | Tailwind CSS utility classes |
| Emoji icons | Lucide React icon components |
| `st.columns` | CSS Grid / Flexbox |
| `st.sidebar` | Fixed sidebar component |
| `st.button` variants | Custom Button component with variant prop |

The colour tokens (Navy, Teal, Gold), spacing scale, and typography should be extracted into a shared `theme.ts` file that both Streamlit CSS and React components reference.
