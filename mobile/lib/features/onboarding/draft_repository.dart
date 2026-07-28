import 'dart:convert';

import '../../core/secure_storage/sensitive_store.dart';
import 'onboarding_models.dart';

final class DraftRepository {
  const DraftRepository(this._store, {this.maxAge = const Duration(days: 30)});

  final SensitiveStore _store;
  final Duration maxAge;

  Future<OnboardingDraft?> restore({DateTime? now}) async {
    final raw = await _store.read(SensitiveKeys.onboardingDraft);
    if (raw == null) return null;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        throw const FormatException('Draft is not an object');
      }
      final draft = OnboardingDraft.fromJson(
        Map<String, dynamic>.from(decoded),
      );
      if (draft.schemaVersion != 1 ||
          draft.isExpired(now ?? DateTime.now(), maxAge: maxAge)) {
        await clear();
        return null;
      }
      return draft;
    } on FormatException {
      await clear();
      return null;
    } on TypeError {
      await clear();
      return null;
    }
  }

  Future<void> save(OnboardingDraft draft) =>
      _store.write(SensitiveKeys.onboardingDraft, jsonEncode(draft.toJson()));

  Future<void> clear() => _store.delete(SensitiveKeys.onboardingDraft);
}
