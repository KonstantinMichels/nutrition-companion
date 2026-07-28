import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/app/providers.dart';
import 'package:nutrition_companion/core/config/app_config.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_controller.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_screen.dart';
import 'package:nutrition_companion/features/profile/profile_repository.dart';

import '../helpers/fake_profile_repository.dart';
import '../helpers/fake_sensitive_store.dart';

void main() {
  testWidgets('system back moves to the previous onboarding step', (
    tester,
  ) async {
    final container = await _containerAtStep(2);
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: OnboardingScreen()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(container.read(onboardingControllerProvider).draft.currentStep, 1);
    expect(find.text('Schritt 2 von 10'), findsOneWidget);
  });

  testWidgets('first onboarding step requires a second back press to leave', (
    tester,
  ) async {
    final container = await _containerAtStep(0);
    addTearDown(container.dispose);
    final router = GoRouter(
      initialLocation: '/onboarding',
      routes: [
        GoRoute(
          path: '/onboarding',
          builder: (_, _) => const OnboardingScreen(),
        ),
        GoRoute(
          path: '/home',
          builder: (_, _) =>
              const AppScaffold(title: 'Hauptseite', body: SizedBox.shrink()),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pump();

    expect(router.state.uri.path, '/onboarding');
    expect(
      find.text('Zum Verlassen der Erstellung erneut Zurück drücken'),
      findsOneWidget,
    );

    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(router.state.uri.path, '/home');
  });

  testWidgets('close button asks for confirmation from second step', (
    tester,
  ) async {
    final container = await _containerAtStep(1);
    addTearDown(container.dispose);
    final router = _onboardingRouter();
    addTearDown(router.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Onboarding schließen'));
    await tester.pumpAndSettle();

    expect(find.text('Erstellung verlassen?'), findsOneWidget);
    expect(find.textContaining('verschlüsselter Entwurf'), findsOneWidget);

    await tester.tap(find.text('Weiter bearbeiten'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, '/onboarding');

    await tester.tap(find.byTooltip('Onboarding schließen'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Erstellung verlassen'));
    await tester.pumpAndSettle();

    expect(router.state.uri.path, '/home');
  });
}

GoRouter _onboardingRouter() => GoRouter(
  initialLocation: '/onboarding',
  routes: [
    GoRoute(path: '/onboarding', builder: (_, _) => const OnboardingScreen()),
    GoRoute(
      path: '/home',
      builder: (_, _) =>
          const AppScaffold(title: 'Hauptseite', body: SizedBox.shrink()),
    ),
  ],
);

Future<ProviderContainer> _containerAtStep(int step) async {
  final container = ProviderContainer(
    overrides: [
      sensitiveStoreProvider.overrideWithValue(FakeSensitiveStore()),
      profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
      appConfigProvider.overrideWithValue(
        AppConfig(
          environment: AppEnvironment.production,
          apiBaseUrl: Uri.parse('https://api.example.test'),
          allowInsecureLocalHttp: false,
        ),
      ),
    ],
  );
  await container
      .read(onboardingControllerProvider.notifier)
      .initialize(fresh: true);
  container.read(onboardingControllerProvider.notifier).jumpTo(step);
  return container;
}
