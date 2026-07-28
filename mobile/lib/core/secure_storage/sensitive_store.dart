import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class SensitiveStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
  Future<void> clearAppData();
}

abstract final class SensitiveKeys {
  static const onboardingDraft = 'sensitive.onboarding_draft.v1';
  static const latestAssessment = 'sensitive.latest_assessment.v1';
  static const currentProfileId = 'sensitive.current_profile_id.v1';
  static const consentState = 'sensitive.consent_state.v1';
  static const values = <String>{
    onboardingDraft,
    latestAssessment,
    currentProfileId,
    consentState,
  };
}

final class FlutterSensitiveStore implements SensitiveStore {
  FlutterSensitiveStore({FlutterSecureStorage? storage})
    : _storage =
          storage ??
          const FlutterSecureStorage(
            // v10 defaults use Android Keystore-backed RSA-OAEP/AES-GCM and
            // migrate away from the deprecated Jetpack Security storage.
            aOptions: AndroidOptions(),
            iOptions: IOSOptions(
              accessibility: KeychainAccessibility.first_unlock_this_device,
            ),
          );

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);

  @override
  Future<void> clearAppData() async {
    // Delete only keys owned by this app. Future authentication secrets can use a
    // separate explicit migration/deletion policy.
    for (final key in SensitiveKeys.values) {
      await _storage.delete(key: key);
    }
  }
}
