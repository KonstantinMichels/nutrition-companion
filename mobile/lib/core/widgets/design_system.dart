import 'package:flutter/material.dart';

import '../../app/theme.dart';

final class NutritionSection extends StatelessWidget {
  const NutritionSection({
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.xl),
    this.backgroundColor,
    this.semanticContainer = false,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? backgroundColor;
  final bool semanticContainer;

  @override
  Widget build(BuildContext context) => Semantics(
    container: semanticContainer,
    child: DecoratedBox(
      decoration: BoxDecoration(
        color:
            backgroundColor ??
            Theme.of(context).colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(AppRadii.section),
      ),
      child: Padding(padding: padding, child: child),
    ),
  );
}

final class NutritionHeroSection extends StatelessWidget {
  const NutritionHeroSection({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      borderRadius: const BorderRadius.vertical(
        bottom: Radius.circular(AppRadii.section),
      ),
    ),
    child: Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.xl,
        MediaQuery.viewPaddingOf(context).top + AppSpacing.xl,
        AppSpacing.xl,
        AppSpacing.xl,
      ),
      child: child,
    ),
  );
}

final class NutritionSubSurface extends StatelessWidget {
  const NutritionSubSurface({
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.md),
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerHigh,
      borderRadius: BorderRadius.circular(AppRadii.large),
    ),
    child: Padding(padding: padding, child: child),
  );
}

final class NutritionSectionHeader extends StatelessWidget {
  const NutritionSectionHeader({
    required this.title,
    this.action,
    this.subtitle,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            if (subtitle != null) ...[
              const SizedBox(height: AppSpacing.xxs),
              Text(
                subtitle!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
      if (action != null) ...[const SizedBox(width: AppSpacing.sm), action!],
    ],
  );
}

final class NutritionActionPill extends StatelessWidget {
  const NutritionActionPill({
    required this.label,
    required this.onPressed,
    this.icon,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => icon == null
      ? FilledButton.tonal(onPressed: onPressed, child: Text(label))
      : FilledButton.tonalIcon(
          onPressed: onPressed,
          icon: Icon(icon, size: 18),
          label: Text(label),
        );
}

final class NutritionQuickAction extends StatelessWidget {
  const NutritionQuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Expanded(
    child: Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadii.medium),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DecoratedBox(
                decoration: BoxDecoration(
                  color: onTap == null
                      ? Theme.of(context).colorScheme.surfaceContainerHighest
                      : Theme.of(context).colorScheme.primaryContainer,
                  shape: BoxShape.circle,
                ),
                child: SizedBox.square(
                  dimension: 52,
                  child: Icon(
                    icon,
                    color: onTap == null
                        ? Theme.of(context).colorScheme.onSurfaceVariant
                        : Theme.of(context).colorScheme.primary,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

final class NutritionFeatureOverview extends StatelessWidget {
  const NutritionFeatureOverview({
    required this.title,
    required this.description,
    required this.icon,
    required this.actionLabel,
    required this.onOpen,
    this.secondaryActionLabel,
    this.onSecondaryOpen,
    super.key,
  });

  final String title;
  final String description;
  final IconData icon;
  final String actionLabel;
  final VoidCallback onOpen;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryOpen;

  @override
  Widget build(BuildContext context) => NutritionSection(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primaryContainer,
            shape: BoxShape.circle,
          ),
          child: SizedBox.square(
            dimension: 48,
            child: Icon(icon, color: Theme.of(context).colorScheme.primary),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: AppSpacing.xs),
              Text(
                description,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.xs,
                runSpacing: AppSpacing.xs,
                children: [
                  NutritionActionPill(label: actionLabel, onPressed: onOpen),
                  if (secondaryActionLabel != null)
                    NutritionActionPill(
                      label: secondaryActionLabel!,
                      onPressed: onSecondaryOpen,
                    ),
                ],
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

final class NutritionListRow extends StatelessWidget {
  const NutritionListRow({
    required this.title,
    this.subtitle,
    this.leading,
    this.trailing,
    this.onTap,
    this.showDivider = true,
    this.isThreeLine = false,
    super.key,
  });

  final Widget title;
  final Widget? subtitle;
  final Widget? leading;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool showDivider;
  final bool isThreeLine;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      ListTile(
        contentPadding: EdgeInsets.zero,
        leading: leading,
        title: title,
        subtitle: subtitle,
        trailing: trailing,
        onTap: onTap,
        isThreeLine: isThreeLine,
      ),
      if (showDivider) const Divider(),
    ],
  );
}
