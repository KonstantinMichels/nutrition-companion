# Nutrition Companion design system

> The N26 references define structural inspiration only. Nutrition Companion
> retains its own existing colors, branding and semantic color system.

## Structural language

Screens use a rhythm of **section → space → section**. A `NutritionSection` is
the primary visual grouping mechanism: one strongly rounded, flat surface holds
several pieces of related content. The screen background remains visible
between sections. Typography, alignment, whitespace, and subtle dividers
separate children inside a section.

Do not turn each fact or list item into an independent card. A screen should
normally contain a small number of meaningful sections rather than a grid or
stack of equally prominent Material cards.

The deepest application layer is always black in light and dark mode. Migrated
section screens reveal this layer between and around their surfaces. Legacy
screens keep a theme-colored compatibility surface until their content has
been migrated, while the underlying scaffold remains black.

## Shape hierarchy

The values live in `AppRadii` in `mobile/lib/app/theme.dart`:

| Token | Radius | Use |
| --- | ---: | --- |
| `small` | 10 dp | thumbnails and compact controls |
| `medium` | 18 dp | inputs and small inner controls |
| `large` | 26 dp | nested surfaces and legacy cards |
| `section` | 32 dp | major sections, dialogs, bottom sheets |
| pill | stadium | contextual and secondary actions |
| circle | circle | limited home-screen quick actions |

Radii must come from these tokens. Feature screens must not invent new radii.

## Spacing

`AppSpacing` provides the scale 4, 8, 12, 16, 20, 24, 32, 40, and 48 dp.

- Screen-to-section margin: 2 dp
- Section-to-section gap: 10 dp by default; 16–24 dp where groups are less
  closely related
- Internal section padding: 24 dp
- Compact section padding: 16 dp
- Row content stays close; unrelated groups receive the larger gap

Spacing communicates grouping. Do not increase every gap indiscriminately.

## Section primitives

### `NutritionSection`

Use for a meaningful screen-level content group: an overview, meals, macros,
hydration, recipe ingredients, pantry items, shopping items, or a related form
group. It uses the current theme's semantic surface color and a 32 dp radius.

### `NutritionSubSurface`

Use for one meaningful highlight inside a section, such as a target or remaining
energy value. Normally allow no more than two surface levels:

```text
NutritionSection
└── NutritionSubSurface
```

Avoid:

```text
Card
└── Card
    └── Card
```

### `NutritionSectionHeader`

Pairs a strong title and optional subtitle with one compact contextual action.
It is not a toolbar and should not contain several competing actions.

## Lists and rows

Related rows belong inside one `NutritionSection`. Use `NutritionListRow` with
whitespace, alignment, and subtle dividers. Do not wrap every food, meal, pantry
lot, recipe, history entry, or shopping item in its own `Card`.

The final row omits its divider. Rows retain adequate touch targets and use a
chevron only when tapping navigates to another view.

## Actions

`NutritionActionPill` is for contextual secondary actions such as “Details”,
“Bearbeiten”, “Filtern”, or “Verlauf”. Do not make every action a pill. A
workflow's primary action remains a prominent filled button.

`NutritionQuickAction` is a circular icon with a label below. Reserve it for a
small set of frequent shortcuts, principally on the home screen. Do not use it
as the default action presentation across the application.

## Floating navigation

The primary navigation is a clipped 32 dp rounded surface with a 12 dp
horizontal margin and an 8 dp safe bottom margin. It sits on the black root
layer rather than attaching a full-width rectangle to the physical screen
edge. Its translucent `surfaceContainerHigh` color is intentionally distinct
from the `surfaceContainerLow` section/card color, with backdrop blur preserving
the layered effect. The selected destination highlights icon and label together
inside one rounded indicator. Its host has no color of its own:
`Scaffold.extendBody` lets page content continue underneath the navigation.
Scroll views provide an 86 dp end inset plus the system gesture inset. This
leaves exactly the 10 dp section gap between final content and the navigation
when scrolled to the end.

## Top-attached hero section

The first Overview surface uses `NutritionHeroSection`. Its background begins
at the physical screen top and extends behind the transparent status bar. Only
its content consumes the status-bar inset. The top corners are unrounded and
the lower corners use the 32 dp section radius, creating the first visible
transition to the black root background. Regular sections retain their normal
four-corner rounding and black separation gaps.

`AppScaffold` applies the top-attached hero treatment to every normal screen.
The hero contains the screen title and existing header actions. Screens that
have not yet split their content into several `NutritionSection` widgets place
their complete body in one near-edge rounded compatibility surface below the
hero. This preserves readability and interaction while following the same
hero → black gap → surface composition.

## Forms, dialogs, and sheets

Related fields share a section; individual inputs do not receive another card.
Inputs use the medium radius and semantic theme surfaces. Dialogs and modal
bottom sheets use the section radius, generous spacing, minimal elevation, and
the existing light/dark theme colors. Interaction patterns should only change
when the workflow itself benefits.

## Color and typography

Components consume `Theme.of(context).colorScheme` and existing semantic
colors. Never hardcode colors sampled from N26 or introduce N26 petrol/green.
The existing type system stays in place; hierarchy may use stronger values,
clear titles, and subdued metadata.

## Review checklist

- Can several standalone cards become one coherent section?
- Does every nested surface highlight a meaningful subgroup?
- Is screen background visible between major sections?
- Are radii and spacing drawn from the shared tokens?
- Are list rows grouped rather than floating independently?
- Is there one clear primary action?
- Do light mode, dark mode, text scaling, and semantic colors still work?
