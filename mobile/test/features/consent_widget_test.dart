import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/app/providers.dart';
import 'package:nutrition_companion/core/config/app_config.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_controller.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_screen.dart';
import 'package:nutrition_companion/features/profile/profile_repository.dart';
import 'package:nutrition_companion/features/privacy/privacy_repository.dart';

import '../helpers/fake_consent_status_reader.dart';
import '../helpers/fake_profile_repository.dart';
import '../helpers/fake_sensitive_store.dart';

void main() {
  testWidgets('consent checkbox is not preselected', (tester) async {
    final store = FakeSensitiveStore();
    final container = ProviderContainer(
      overrides: [
        sensitiveStoreProvider.overrideWithValue(store),
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
    container.read(onboardingControllerProvider.notifier).jumpTo(7);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: OnboardingScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final checkbox = tester.widget<CheckboxListTile>(
      find.byKey(const Key('consent-checkbox')),
    );
    expect(checkbox.value, isFalse);
    expect(
      find.textContaining('Textversion: privacy_consent_de_mvp_v1'),
      findsOneWidget,
    );
  });

  testWidgets('active consent is shown as checked status', (tester) async {
    final container = ProviderContainer(
      overrides: [
        sensitiveStoreProvider.overrideWithValue(FakeSensitiveStore()),
        profileRepositoryProvider.overrideWithValue(
          FakeProfileRepository(
            bundle: const ProfileBundle(
              profile: {},
              activity: {},
              goal: {},
              restrictions: [],
              health: {},
            ),
          ),
        ),
        assessmentConsentStatusReaderProvider.overrideWithValue(
          const FakeConsentStatusReader(true),
        ),
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
    container.read(onboardingControllerProvider.notifier).jumpTo(7);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: OnboardingScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final checkbox = tester.widget<CheckboxListTile>(
      find.byKey(const Key('consent-checkbox')),
    );
    expect(checkbox.value, isTrue);
    expect(find.text('Einwilligung bereits wirksam erteilt'), findsOneWidget);
    expect(find.textContaining('Aktiv für Textversion'), findsOneWidget);
  });
}
