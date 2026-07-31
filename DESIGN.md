---
name: Truck Tracker
description: Internal dispatch tool for a car-hauling operation — zone-based trip tracking, cargo logging, and billing.
colors:
  ink-slate: "#0f172a"
  ink-slate-hover: "#1e293b"
  surface-app: "#f8fafc"
  surface-card: "#ffffff"
  surface-subtle: "#f1f5f9"
  border-hairline: "#e2e8f0"
  text-primary: "#0f172a"
  text-secondary: "#475569"
  text-tertiary: "#64748b"
  text-muted: "#94a3b8"
  status-progress-bg: "#fef3c7"
  status-progress-text: "#92400e"
  status-done-bg: "#d1fae5"
  status-done-text: "#065f46"
  danger-bg: "#fef2f2"
  danger-bg-hover: "#fee2e2"
  danger-text: "#b91c1c"
typography:
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "1.5"
  title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: "1.3"
    letterSpacing: "-0.01em"
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: "1.4"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "20px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink-slate}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  button-primary-hover:
    backgroundColor: "{colors.ink-slate-hover}"
  button-danger:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger-text}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
  button-danger-hover:
    backgroundColor: "{colors.danger-bg-hover}"
  card:
    backgroundColor: "{colors.surface-card}"
    rounded: "{rounded.lg}"
    padding: "20px"
  input:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
---

# Design System: Truck Tracker

## Overview

**Creative North Star: "The Dispatch Board"**

A clipboard, not a showroom. This is an internal ops tool for one car-hauling business — the two people using it (dispatch staff at a desk, drivers on a phone) need to read a status, find a button, and move on. The system deliberately withholds decoration: one neutral ink color for structure and action, three semantic colors reserved strictly for trip status (in progress / completed / destructive), and nothing else competing for attention. Whitespace and hairline borders do the organizing work that color would do in a consumer product.

Nothing here is provisional-looking or unfinished — the restraint is the choice, not a placeholder for a future rebrand. If this system ever gets a real brand pass, the ink-slate primary is the one color to replace; everything else (status colors, neutral scale) is functional and should survive unchanged.

**Key Characteristics:**
- Single ink-slate (`#0f172a`) as the only color with authority — it is text, primary buttons, and active tab state, never anything else.
- Status color (amber = in progress, emerald = completed, red = destructive) never appears outside a `Badge` or a delete affordance.
- Flat cards on a barely-tinted app background (`#f8fafc` vs `#ffffff`) — the only depth cue in the system.
- Dense, left-aligned, form-first layouts. No hero sections, no marketing rhythm.

## Colors

Cool slate neutrals carry the entire interface; color is rationed to exactly three semantic meanings.

### Primary
- **Ink Slate** (`#0f172a`): the single accent. Used for primary buttons, the active tab underline/text, and body text. Hover state is Ink Slate Hover (`#1e293b`), a half-step lighter — the only state change primary buttons get.

### Neutral
- **App Canvas** (`#f8fafc`): page background, sits behind every card.
- **Card White** (`#ffffff`): every card, input, and the header bar.
- **Subtle Fill** (`#f1f5f9`): the segmented login toggle's track, the inactive half of two-state controls.
- **Hairline** (`#e2e8f0`): every border — card edges, dividers between list rows, the tab strip's bottom rule. Never a shadow where a hairline will do.
- **Text Primary** (`#0f172a`): headings, row titles, primary values (amounts, plates, names).
- **Text Secondary** (`#475569`): supporting line under a title (route, subtitle).
- **Text Tertiary** (`#64748b`): nav links, secondary actions ("Ver carros", "Salir").
- **Text Muted** (`#94a3b8`): timestamps, placeholder copy, empty-state text.

### Named Rules
**The One Ink Rule.** Ink Slate is the only color allowed to mean "this is interactive and important." If a second color starts appearing on primary buttons or active nav, the system has drifted.

**The Status-Only Rule.** Amber, emerald, and red never appear as decoration. Amber = trip in progress, emerald = trip completed, red = a destructive action or an error message. No other use is permitted, ever — a red icon that doesn't mean "delete" or "error" is a bug in this system, not a style choice.

## Typography

**Body Font:** ui-sans-serif, system-ui, -apple-system, sans-serif (the platform's native UI font stack — no webfont is loaded)

**Character:** Plain and legible over expressive. The system uses exactly three weights (400 regular body, 500 medium labels/buttons, 600 semibold titles) and never strays into display-scale type; the largest text on screen is a 24px page title.

### Hierarchy
- **Title** (600, 24px, 1.3 line-height, -0.01em tracking): page-level heading only ("Truck Tracker" in the header, "Iniciar sesión" / "Crear cuenta" on the login card).
- **Section Label** (600, 14px): card headers inside `Card` — "Nuevo camión", "Usuarios", "Viaje en curso".
- **Body** (400, 14px, 1.5 line-height): everything else — row content, form values, descriptions.
- **Label** (500, 14px): form field labels, buttons, nav tab text.
- **Micro** (400, 12px): timestamps, badges, empty-state copy, helper text under a form.

### Named Rules
**The No-Display-Type Rule.** There is no hero/display scale in this system. 24px is the ceiling. If a screen needs a bigger number to draw the eye, that's a layout or color problem, not a typography one.

## Layout

Single-column, capped-width layouts throughout — this is a form-and-list tool, never a canvas.

- **Login**: centered card, `max-w-sm` (384px), vertically centered in the viewport.
- **App shell**: header bar (white, hairline bottom border) + `max-w-5xl` (1024px) content column, horizontally centered with 16px side padding.
- **Admin panel**: horizontal tab strip (hairline bottom border, active tab gets an ink-slate underline) above a single active section — no persistent sidebar.
- **Driver view**: single scrolling column of stacked cards (`space-y-6`, 24px gap) — active trip (or the start-trip form) first, history card below. No tabs; there is only one thing to do at a time.
- **Forms**: fields stack vertically at 12–16px gaps; inline forms (create-truck, create-zone) go single-row on wide viewports and wrap to a column on narrow ones (`flex-col sm:flex-row`).
- **Lists**: hairline-divided rows (`divide-y`) inside a card, never a bordered table grid.

## Elevation & Depth

Nearly flat. The only shadow in the system is `shadow-sm` on `Card` and the header bar — a barely-there lift used purely to separate a white surface from the tinted app background, not to imply stacking order or interactivity.

### Shadow Vocabulary
- **Card rest** (`box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)` — Tailwind `shadow-sm`): applied to every `Card` and the app header. No hover elevation change exists anywhere; nothing lifts on interaction.

### Named Rules
**The Flat-By-Default Rule.** Depth comes from the App Canvas / Card White contrast and hairline borders first; shadow is a secondary, barely-perceptible reinforcement, never the primary depth cue.

## Shapes

- **Cards**: `rounded-xl` (12px) — the softest radius in the system, reserved for the largest surfaces.
- **Buttons, inputs, selects, badges (pill)**: `rounded-lg` (8px) for rectangular controls; `rounded-full` for the role `Badge`.
- **Segmented control track** (login mode toggle): `rounded-lg` outer, `rounded-md` (6px) on the active pill inside it — one step tighter than its parent, per the system's nesting convention (child radius ≤ parent radius).
- **Borders**: 1px hairline (`border-slate-200`) on cards, inputs, and dividers. No double borders, no border + shadow stacking.

### Named Rules
**The Nesting Radius Rule.** A control nested inside a larger rounded surface uses an equal or smaller radius than its parent — never larger. Card (12px) → button/input inside it (8px) → active-state pill inside a toggle (6px).

## Components

### Buttons
- **Shape:** `rounded-lg` (8px), no border.
- **Primary:** Ink Slate background, white text, 500-weight, `px-3 py-1.5` at row scale or `py-2.5` full-width on forms. Disabled state drops to 50% opacity — no other visual disabled treatment.
- **Hover:** background steps to Ink Slate Hover (`#1e293b`); no scale, shadow, or transform change, just the color step, on a 150–200ms transition.
- **Danger:** red-50 background, red-700 text (not white-on-red) — a quiet destructive style that reads as "careful" rather than "alarming"; hover deepens to red-100.
- **Ghost:** transparent background, `text-slate-600`, hover fills `bg-slate-100`. Used for low-emphasis actions (currently unused but defined for future secondary actions).

### Badges
- **Style:** `rounded-full` pill, `px-2 py-0.5`, 12px medium text, no border — a flat tinted-background chip.
- **Tones:** slate (default/role labels), amber (trip in progress), emerald (trip completed), red (reserved, currently unused by any live badge).

### Cards / Containers
- **Corner Style:** `rounded-xl` (12px).
- **Background:** Card White on App Canvas.
- **Shadow Strategy:** `shadow-sm` only (see Elevation).
- **Border:** 1px hairline all around; an internal 1px hairline separates an optional header row (title + action) from the body.
- **Internal Padding:** 20px (`p-5`) body; header row gets 20px horizontal / 16px vertical.

### Inputs / Selects
- **Style:** white fill, 1px hairline border, `rounded-lg`, `px-3 py-2`, 14px text.
- **Focus:** border shifts to Ink Slate plus a 1px Ink Slate focus ring (`focus:ring-1`) — no glow, no color change beyond the ink accent.
- **Disabled / Error:** not yet defined anywhere in the implementation; treat as undecided rather than inferring a pattern.

### Navigation (Admin tab strip)
- **Style:** horizontal row of text buttons, 14px medium, bottom-aligned to a shared hairline rule.
- **Default:** `text-slate-500`.
- **Hover:** `text-slate-700`.
- **Active:** `text-slate-900` plus a 2px Ink Slate underline (`border-b-2`) — the underline is the only active-state indicator; no background fill.
- **Mobile:** no distinct treatment observed; the tab strip does not currently adapt below desktop width.

### Driver Trip Card (signature component)
The one component unique to this system: a single card that is either the "start a trip" form (three selects + submit) or, once a trip exists, flips to a status readout (plate, route, departure time, a single "Marcar como llegado" primary button) — never both at once. It's a state machine rendered as one card, not two screens.

## Do's and Don'ts

### Do:
- **Do** keep Ink Slate as the only color used for primary actions and active navigation state (The One Ink Rule).
- **Do** reserve amber/emerald/red strictly for trip status and destructive actions (The Status-Only Rule).
- **Do** use hairline borders + the App Canvas/Card White contrast as the primary depth cue before reaching for shadow.
- **Do** keep nested radii equal to or smaller than their parent container's radius.
- **Do** design the driver surface for one-handed phone use first — it is read in the field, not at a desk.

### Don't:
- **Don't** introduce a second "important" color alongside Ink Slate; route any new emphasis need through weight, size, or spacing instead.
- **Don't** add hover elevation/lift to cards or buttons — this system has committed to flat, color-only state changes.
- **Don't** invent sample fleet, driver, or trip data to demo the UI — PRODUCT.md records that no real data exists yet; use honest empty states instead.
- **Don't** add a display/hero type scale; 24px is the largest text this system uses anywhere.
