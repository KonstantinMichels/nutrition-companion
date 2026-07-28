import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/app/providers.dart';
import 'package:nutrition_companion/core/config/app_config.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_controller.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_screen.dart';
import 'package:nutrition_companion/features/profile/profile_repository.dart';

import '../helpers/fake_profile_repository.dart';
import '../helpers/fake_sensitive_store.dart';

void main() {
  testWidgets('explains the physiological reference categories', (
    tester,
  ) async {
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
    addTearDown(container.dispose);
    await container
        .read(onboardingControllerProvider.notifier)
        .initialize(fresh: true);
    container.read(onboardingControllerProvider.notifier).jumpTo(1);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: OnboardingScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Berechnungsdaten'), findsOneWidget);

    await tester.tap(find.text('Physiologische Referenzkategorie'));
    await tester.pumpAndSettle();

    expect(find.text('Männliche Physiologie'), findsOneWidget);
    expect(find.text('Weibliche Physiologie'), findsOneWidget);
    expect(
      find.textContaining('keine Aussage über deine Geschlechtsidentität'),
      findsOneWidget,
    );
  });
}
