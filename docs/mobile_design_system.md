# Mobile design direction

## Goal

The mobile client uses a calm, content-first interface inspired by the clarity
and hierarchy of modern mobile banking apps. It must remain an independent
product design: no N26 trademarks, assets, copy, or exact screen reproductions.
The existing green Material color scheme remains unchanged.

## Principles

1. Show the most relevant value or next action first.
2. Prefer whitespace and typography over borders and decoration.
3. Keep cards flat, grouped, and consistently rounded.
4. Use one clear primary action per view.
5. Keep the five primary destinations visible in the bottom navigation.
6. Put less frequent destinations on the dedicated `Mehr` page, not in an
   overlay menu.
7. Preserve equivalent hierarchy and contrast in light and dark mode.

## Navigation hierarchy

The persistent bottom navigation contains:

- `Start` → `/home`
- `Plan` → `/daily-plan`
- `Verzehr` → `/consumption`
- `Vorrat` → `/pantry`
- `Mehr` → `/more`

The `Mehr` page groups weekly planning, automation, shopping, foods, recipes,
training, progress, history, profile, privacy, and settings. Detail routes keep
the bottom navigation visible and select the closest primary destination.

## Shared tokens

Global spacing, card radius, app-bar styling, navigation styling, and control
themes belong in `mobile/lib/app/theme.dart`. Feature screens should consume
`Theme.of(context)` and shared layout widgets instead of defining colors or
component shapes locally.

Current foundation:

- page padding: 20 dp
- section spacing: 24 dp
- card radius: 16 dp
- flat app bars and cards
- 72 dp bottom navigation with icon and label

## Incremental rollout

1. Validate navigation and the `Mehr` information architecture.
2. Redesign the home screen as the reference screen.
3. Extract repeated metric, list-row, section-header, and action components.
4. Apply those components to planning, consumption, and pantry.
5. Migrate secondary feature screens and verify dark mode, text scaling,
   accessibility labels, and touch target sizes.

Each step should retain existing routes and domain behavior. Visual changes do
not require backend or persistence changes.
