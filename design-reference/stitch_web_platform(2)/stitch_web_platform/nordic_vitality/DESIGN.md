---
name: Nordic Vitality
colors:
  surface: '#e8fef6'
  surface-dim: '#c9dfd7'
  surface-bright: '#e8fef6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#e2f9f0'
  surface-container: '#ddf3eb'
  surface-container-high: '#d7ede5'
  surface-container-highest: '#d1e7df'
  on-surface: '#0c1f1a'
  on-surface-variant: '#414846'
  inverse-surface: '#21342f'
  inverse-on-surface: '#dff6ed'
  outline: '#717976'
  outline-variant: '#c1c8c5'
  surface-tint: '#41655d'
  primary: '#002620'
  on-primary: '#ffffff'
  primary-container: '#173c35'
  on-primary-container: '#81a69d'
  inverse-primary: '#a8cfc4'
  secondary: '#006b54'
  on-secondary: '#ffffff'
  secondary-container: '#9af4d5'
  on-secondary-container: '#007259'
  tertiary: '#192500'
  on-tertiary: '#ffffff'
  tertiary-container: '#2a3c00'
  on-tertiary-container: '#89ab41'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c3ebe0'
  primary-fixed-dim: '#a8cfc4'
  on-primary-fixed: '#00201b'
  on-primary-fixed-variant: '#294d46'
  secondary-fixed: '#9af4d5'
  secondary-fixed-dim: '#7ed7b9'
  on-secondary-fixed: '#002118'
  on-secondary-fixed-variant: '#00513f'
  tertiary-fixed: '#cbf07d'
  tertiary-fixed-dim: '#afd364'
  on-tertiary-fixed: '#141f00'
  on-tertiary-fixed-variant: '#374e00'
  background: '#e8fef6'
  on-background: '#0c1f1a'
  surface-variant: '#d1e7df'
typography:
  display:
    fontFamily: Manrope
    fontSize: 3.5rem
    fontWeight: '800'
    lineHeight: 4rem
    letterSpacing: -0.03em
  headline-xl:
    fontFamily: Manrope
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.75rem
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Manrope
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 2rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Manrope
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  stat-counter:
    fontFamily: Manrope
    fontSize: 2rem
    fontWeight: '800'
    lineHeight: 2.25rem
    letterSpacing: -0.03em
  body-lg:
    fontFamily: Manrope
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
  body-md:
    fontFamily: Manrope
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-sm:
    fontFamily: Manrope
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  label-md:
    fontFamily: Manrope
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Manrope
    fontSize: 0.75rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.03em
  caption:
    fontFamily: Manrope
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-sm: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system embodies a modern, high-end wellness SaaS ethos: restorative, precise, and encouraging. Designed for active individuals, athletic coaches, and wellness enthusiasts who value data without clinical coldness, the aesthetic balances the disciplined rigor of sports analytics with organic tranquility. 

The visual style blends Scandinavian minimalism with rich, bio-centric tones: crisp layouts, breathable white space, ultra-subtle structural lines, and vibrant kinetic accents that celebrate personal progress. Interfaces feel airy, calm, and effortlessly premium—evoking holistic vitality rather than industrial mechanical fitness.

## Colors
The palette grounds deep botanical pigments against soft ambient surfaces, illuminated by energetic lifestyle accents:

- **Primary Forest & Emerald:** Deep Forest Green (`#173C35`) serves as the core anchor for authoritative typography, dark surfaces, and primary key active states. Emerald Green (`#27866C`) powers focused interactions, primary buttons, and key analytical highlights.
- **Accents:** Fresh Lime (`#C5EA78`) is reserved for motivation metrics, completed rings, PR badges (особисті рекорди), and high-tempo charts. Soft Warm Orange (`#F4A261`) signals calorie expenditure, cardiovascular zones, and secondary targets.
- **Surfaces & Backgrounds:** The background foundation uses Warm Off-White (`#F6F8F5`), layered with crisp container White (`#FFFFFF`) and Soft Mint tints (`#DDF3E8`) for metric callouts and highlighted states.
- **Text & Neutral Contrast:** Text Primary (`#182B26`) delivers dark contrast without pure black severity. Text Secondary (`#687A73`) ensures comfortable hierarchy for secondary labels, table headers, and timestamp metadata.
- **Semantic Feedback:**
  - Success: `#289E68` (виконано / норма)
  - Warning: `#E59500` (увага / дефіцит)
  - Error: `#D64545` (перевищення / помилка)
  - Info: `#3B82F6` (синхронізація / сповіщення)
  - Disabled: `#E1E6E3` with `#9DAEA7` text.

## Typography
Manrope delivers modern geometric clarity with open counters and balanced Cyrillic character forms, essential for localized Ukrainian fitness analytics (such as «Показники», «Тренування», «Відновлення»). 

- **Numerical Hierarchy:** Statistical metric callouts leverage `stat-counter` and `display` weights with tight letter-spacing and tabular numeral figures (`font-variant-numeric: tabular-nums`) so daily steps, kcal, and heart rate values remain horizontally steady during real-time updates.
- **Labels & Microcopy:** Data headers, graph axes, and tags utilize uppercase or sentence-cased `label-sm` with slight positive tracking to preserve legibility when paired with dense data representations.

## Layout & Spacing
Built strictly on an 8px grid foundation (with 4px half-steps for micro-components and badges), the layout uses a responsive shell designed for rich dashboard exploration:

- **Navigation Shell:** Desktop views feature a persistent vertical sidebar (260px fixed width) coupled with a top header (72px fixed height) for quick date-range pickers and user profile controls. On mobile, the sidebar collapses into a streamlined bottom navigation bar (56px) and an off-canvas drawer.
- **Grid Architecture:** Desktop analytics use a 12-column fluid grid system with 24px (`1.5rem`) gutters and 32px (`2rem`) margins. Tablet views compress to an 8-column layout with 16px gutters, and mobile screens conform to a single-column or 2-column card stack with 16px margins.
- **Card Clustering:** Primary metrics cluster together using `space-md` gaps. Segmented analytics (such as heart rate zones, activity splits, and sleep architecture) group logically with `space-lg` separation to avoid visual density fatigue.

## Elevation & Depth
Depth relies on ambient, organic diffusion paired with 1px low-contrast boundary lines rather than heavy drop shadows:

- **Level 0 (Canvas Base):** Warm Off-White (`#F6F8F5`), flat and unshadowed.
- **Level 1 (Dashboard Cards & Panels):** Pure White (`#FFFFFF`) with a delicate 1px border in `#E6EDE8` and an ambient, forest-tinted shadow: `0 4px 20px -2px rgba(23, 60, 53, 0.04), 0 2px 6px -1px rgba(23, 60, 53, 0.02)`.
- **Level 2 (Interactive Cards Hover & Popovers):** Elevated on hover or expansion: `0 12px 28px -4px rgba(23, 60, 53, 0.08), 0 4px 10px -2px rgba(23, 60, 53, 0.03)`.
- **Level 3 (Modals & Drawer Panels):** Float atop an ambient backdrop overlay (`rgba(24, 43, 38, 0.4)` with 4px backdrop-blur): `0 24px 48px -8px rgba(23, 60, 53, 0.16)`.
- **Level 4 (Toasts & Notifications):** Anchored top-right or bottom-center: `0 10px 30px rgba(23, 60, 53, 0.12)`.

## Shapes
A roundedness factor of 2 underpins the UI geometry, establishing welcoming, ergonomic contours:

- Standard data cards, dashboard widgets, and analytical modules feature a uniform 16px (`1rem`) border radius (`rounded-lg`).
- Interactive inputs, select dropdowns, and button elements use 10px to 12px radius (`rounded-md`).
- Metric badges, status chips, and avatar containers utilize full pill rounding (`9999px`) to create striking contrast against the squared card matrices.
- Icon containers and small graphical anchors take an 8px radius (`rounded-sm`).

## Components

### Buttons
- **Primary:** Filled Emerald Green (`#27866C`) background with White text, transitioning to `#173C35` on hover. 12px horizontal padding, 10px vertical padding, semi-bold 14px text. Focus ring: 2px offset with `#C5EA78`.
- **Secondary:** Soft Mint tint (`#DDF3E8`) with Deep Forest Green text (`#173C35`). On hover, gains an emerald wash.
- **Outline:** Transparent background, 1px solid `#D5E0DA`, `#182B26` text. Hover brings `#F0F6F2` surface tint.
- **Destructive:** Pale red tint (`#FDE8E8`) with `#D64545` text.

### Metric Cards (Картки показників)
White background (`#FFFFFF`), 16px border radius, 1px solid border (`#E6EDE8`), 20px internal padding. Top row contains a small muted icon, Ukrainian metric label (e.g., «Спалені калорії», «Пульс у спокої»), and an optional delta pill (+4.2%). Center showcases the bold numerical value (`stat-counter`) with unit descriptor (`ккал`, `уд/хв`), followed by mini progress bars or sparkline charts at the base.

### Chips & Badges
- **Status Chips:** Pill-shaped, 6px vertical / 12px horizontal padding. Composed of an 8px circular status pip and label text in `label-sm`.
  - Normal/Active: Mint surface (`#DDF3E8`) with Emerald text (`#27866C`).
  - Personal Record: Lime surface (`#EDF9D4`) with Forest text (`#173C35`).
- **Interactive Filter Chips:** Outline style with 1px border (`#D5E0DA`). Selected state fills with `#173C35` and white text.

### Form Inputs & Date Range Selectors
White background, 1px border (`#D5E0DA`), 10px radius, 12px horizontal padding, `#182B26` value text, and `#687A73` placeholder. Focus state applies a 1px border of `#27866C` alongside a subtle 3px box-shadow glow in `rgba(39, 134, 108, 0.15)`.

### Checkboxes & Radios
Custom 20px inputs with 6px border radius for checkboxes and round for radios. Unchecked: 1.5px border in `#CBD8D2`. Checked: Solid `#27866C` fill with a sharp white checkmark or inner dot.

### Activity Rings & Progress Indicators
Circular progress rings feature an unfulfilled track in `#E8EFEA` (stroke width 8-12px) paired with single-tone or gradient stroke caps in `#27866C`, `#C5EA78`, and `#F4A261` representing Steps («Кроки»), Active Time («Активність»), and Calories («Калорії»).

### Data Tables & Workout Logs (Журнал тренувань)
Header row features uppercase `label-sm` in `#687A73`, bottom-bordered by 1px solid `#E6EDE8`. Body rows maintain 52px height, soft zebra striping (`#FAFBF9`) on hover, inline metric tags, and action icon triggers aligned to the right.