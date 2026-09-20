import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/design_system.dart';

final class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Mehr',
    revealRootBackground: true,
    body: ContentWidth(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _section(context, 'Planung', const [
            _Entry(
              Icons.calendar_view_week_outlined,
              'Wochenplan',
              '/weekly-plan',
            ),
            _Entry(
              Icons.auto_awesome_outlined,
              'Plan-Automatisierung',
              '/meal-plan-automation',
            ),
            _Entry(Icons.shopping_cart_outlined, 'Einkauf', '/shopping-lists'),
          ]),
          const SizedBox(height: 20),
          _section(context, 'Inhalte', const [
            _Entry(Icons.restaurant_outlined, 'Lebensmittel', '/foods'),
            _Entry(Icons.menu_book_outlined, 'Rezepte', '/recipes'),
            _Entry(Icons.fitness_center_outlined, 'Training', '/training'),
          ]),
          const SizedBox(height: 20),
          _section(context, 'Auswertung & Konto', const [
            _Entry(Icons.show_chart, 'Fortschritt', '/progress'),
            _Entry(Icons.history, 'Verlauf', '/history'),
            _Entry(Icons.person_outline, 'Profil bearbeiten', '/profile'),
            _Entry(
              Icons.privacy_tip_outlined,
              'Datenschutz & Daten',
              '/privacy',
            ),
            _Entry(Icons.settings_outlined, 'Einstellungen', '/settings'),
          ]),
          const SizedBox(height: 32),
        ],
      ),
    ),
  );

  Widget _section(BuildContext context, String title, List<_Entry> entries) =>
      NutritionSection(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            NutritionSectionHeader(title: title),
            const SizedBox(height: AppSpacing.sm),
            for (var index = 0; index < entries.length; index++)
              NutritionListRow(
                leading: Icon(entries[index].icon),
                title: Text(entries[index].label),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.go(entries[index].path),
                showDivider: index < entries.length - 1,
              ),
          ],
        ),
      );
}

final class _Entry {
  const _Entry(this.icon, this.label, this.path);

  final IconData icon;
  final String label;
  final String path;
}
