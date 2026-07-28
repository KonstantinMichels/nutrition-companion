import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/core/secure_storage/sensitive_store.dart';
import 'package:nutrition_companion/features/onboarding/draft_repository.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_models.dart';

import '../helpers/fake_sensitive_store.dart';

void main() {
  test('round-trips a sensitive onboarding draft', () async {
    final store = FakeSensitiveStore();
    final repository = DraftRepository(store);
    final draft = OnboardingDraft.initial(
      DateTime.utc(2026, 7, 1),
    ).withField('weight_kg', '82,5', DateTime.utc(2026, 7, 2));

    await repository.save(draft);
    final restored = await repository.restore(now: DateTime.utc(2026, 7, 3));

    expect(restored?.weightKg, '82,5');
    expect(restored?.clientRequestId, draft.clientRequestId);
    expect(store.values.keys, contains(SensitiveKeys.onboardingDraft));
  });

  test('deletes an expired draft on restore', () async {
    final store = FakeSensitiveStore();
    final repository = DraftRepository(store);
    await repository.save(OnboardingDraft.initial(DateTime.utc(2026, 1, 1)));

    final restored = await repository.restore(now: DateTime.utc(2026, 2, 2));

    expect(restored, isNull);
    expect(store.values, isEmpty);
  });

  test('deletes corrupt serialized data', () async {
    final store = FakeSensitiveStore();
    store.values[SensitiveKeys.onboardingDraft] = jsonEncode([
      'not',
      'an',
      'object',
    ]);
    final repository = DraftRepository(store);

    expect(await repository.restore(), isNull);
    expect(store.values, isEmpty);
  });

  test('deletes a draft with incompatible field types', () async {
    final store = FakeSensitiveStore();
    store.values[SensitiveKeys.onboardingDraft] = jsonEncode({
      'schema_version': {'unexpected': true},
      'updated_at': '2026-07-01T00:00:00Z',
    });
    final repository = DraftRepository(store);

    expect(await repository.restore(), isNull);
    expect(store.values, isEmpty);
  });
}
