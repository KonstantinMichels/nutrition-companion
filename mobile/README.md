# Nutrition Companion mobile app

Android-first Flutter client for the Nutrition Companion MVP. All user-facing copy is currently German. The temporary package identifier `com.example.nutrition_companion` must be replaced before publication.

## Prerequisites

- Flutter 3.44.x stable (Dart 3.12.x)
- Java 17
- Android SDK for the Flutter 3.44 stable toolchain
- Android API 24 or newer device/emulator

The current development baseline is Flutter 3.44.8 with Dart 3.12.2. Verification on 2026-07-29 completed static analysis, all 34 mobile tests and the Android debug APK build successfully. Run the commands below to reproduce the checks. iOS compilation was not attempted because the development host runs Linux.

```sh
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --debug \
  --dart-define=APP_ENV=development \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ALLOW_INSECURE_LOCAL_HTTP=true
```

## Local Android run

The Android emulator reaches a host backend through `10.0.2.2`:

```sh
flutter run \
  --dart-define=APP_ENV=development \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ALLOW_INSECURE_LOCAL_HTTP=true
```

For a USB-connected physical device, ADB port reversal is the simplest option and does not require exposing the backend on the LAN:

```sh
adb devices
adb -s <device-id> reverse tcp:8000 tcp:8000
flutter run -d <device-id> \
  --dart-define=APP_ENV=development \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=ALLOW_INSECURE_LOCAL_HTTP=true
```

A private LAN address such as `http://192.168.1.20:8000` is an alternative, but requires an intentional backend bind and restricted firewall access. Plain HTTP is rejected unless all three conditions hold: development environment, explicit opt-in, and a loopback/emulator/private-network host.

Staging and production configuration requires HTTPS:

```sh
flutter run --release \
  --dart-define=APP_ENV=production \
  --dart-define=API_BASE_URL=https://api.example.invalid
```

The release Android variant is intentionally unsigned. Configure a protected release keystore and signing workflow before a release build or publication; never commit its secrets.

The iOS project contains the current Flutter scene lifecycle and the Keychain entitlement required by secure storage. Placeholder AppIcon catalog slots still need real PNG artwork before an iOS archive or publication.

## Local data

Sensitive state uses `flutter_secure_storage` 10 with its Android Keystore-backed RSA-OAEP/AES-GCM defaults and iOS Keychain compatibility. Android backup is disabled. SharedPreferences contains only `ui.theme_mode`.

Owned secure keys are:

- `sensitive.onboarding_draft.v1`: unfinished serialized onboarding state and idempotency UUID; expires after 30 days.
- `sensitive.latest_assessment.v1`: minimal latest summary and cache timestamp; older than 24 hours is visibly marked stale.
- `sensitive.current_profile_id.v1`: reserved for the development resolver boundary; currently not written.
- `sensitive.consent_state.v1`: reserved for a future minimal offline consent indicator; currently not written.

Corrupt or expired drafts are deleted. Complete profile deletion clears all owned secure keys. History deletion also clears the local assessment cache. The secure-storage v10 Android default uses `resetOnError: true`; if Keystore-protected data becomes unrecoverable, the affected local secure store can be reset rather than returning corrupt plaintext. iOS Keychain data can likewise become unavailable after key/device changes. Authoritative backend data is not silently reconstructed into an onboarding draft.

JSON export is created in the application temporary directory only after explicit action, handed to the system share sheet, and deleted after the share call completes. The app never automatically uploads an export.

## API contract used by the client

The client follows the versioned backend contract under `/api/v1`:

- profile, activity, goal, restrictions, and health screening are saved through separate typed `PUT` requests;
- consent version is `privacy_consent_de_mvp_v1` and an active matching consent is reused on a retry;
- assessment creation sends `{ "client_request_id": "<UUID>" }`, preserving that UUID in the encrypted draft for idempotent retry;
- assessment reports use root metadata plus `summary`, `metrics`, and `safety_flags`;
- history and complete-profile deletion send `{ "confirm": true }` in the DELETE body;
- privacy export is treated as an opaque JSON envelope and never logged.

No nutrition calculation is duplicated in Flutter. Offline behavior is limited to an unfinished encrypted draft and the minimal latest-summary cache.
