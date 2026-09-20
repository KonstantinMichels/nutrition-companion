import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/app/theme.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/core/widgets/design_system.dart';

void main() {
  test('root background and layout tokens remain intentional', () {
    expect(AppTheme.light().scaffoldBackgroundColor, Colors.black);
    expect(AppTheme.dark().scaffoldBackgroundColor, Colors.black);
    expect(AppLayout.sectionOuterMargin, 2);
    expect(AppLayout.navigationHorizontalMargin, 12);
    expect(
      AppLayout.navigationContentInset,
      AppLayout.navigationHeight +
          AppLayout.navigationBottomMargin +
          AppLayout.sectionGap,
    );
    expect(AppRadii.section, 32);
    expect(
      AppTheme.light().navigationBarTheme.backgroundColor,
      isNot(AppTheme.light().cardTheme.color),
    );
  });

  testWidgets('primary navigation is clipped into a floating surface', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(
          path: '/home',
          builder: (_, _) => const AppScaffold(
            title: 'Übersicht',
            body: NutritionSection(child: Text('Inhalt')),
            revealRootBackground: true,
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MaterialApp.router(theme: AppTheme.light(), routerConfig: router),
    );
    await tester.pumpAndSettle();

    final navigation = find.byKey(const Key('primary-navigation'));
    expect(navigation, findsOneWidget);
    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
    expect(scaffold.extendBody, isTrue);
    expect(AppTheme.light().navigationBarTheme.backgroundColor!.a, lessThan(1));
    final clip = tester.widget<ClipRRect>(
      find.ancestor(of: navigation, matching: find.byType(ClipRRect)),
    );
    expect(
      clip.borderRadius,
      const BorderRadius.all(Radius.circular(AppRadii.section)),
    );
    expect(
      find.ancestor(of: navigation, matching: find.byType(SafeArea)),
      findsOneWidget,
    );
    final selected = tester.widget<AnimatedContainer>(
      find.byKey(const Key('primary-navigation-destination-0')),
    );
    final selectedDecoration = selected.decoration as BoxDecoration;
    expect(
      selectedDecoration.color,
      AppTheme.light().colorScheme.primaryContainer,
    );
    expect(
      find.descendant(of: navigation, matching: find.text('Start')),
      findsOneWidget,
    );
  });

  testWidgets('hero surface attaches to the top and rounds only its bottom', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: const MediaQuery(
          data: MediaQueryData(viewPadding: EdgeInsets.only(top: 30)),
          child: NutritionHeroSection(child: Text('Hero')),
        ),
      ),
    );

    final decoration =
        tester
                .widget<DecoratedBox>(
                  find.descendant(
                    of: find.byType(NutritionHeroSection),
                    matching: find.byType(DecoratedBox),
                  ),
                )
                .decoration
            as BoxDecoration;
    expect(
      decoration.borderRadius,
      const BorderRadius.vertical(bottom: Radius.circular(AppRadii.section)),
    );
    final padding = tester.widget<Padding>(
      find.descendant(
        of: find.byType(NutritionHeroSection),
        matching: find.byType(Padding),
      ),
    );
    expect((padding.padding as EdgeInsets).top, 30 + AppSpacing.xl);
  });
}
