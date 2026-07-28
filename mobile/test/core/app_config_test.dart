import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/core/config/app_config.dart';

void main() {
  group('AppConfig transport guard', () {
    test('accepts HTTPS in production', () {
      final config = AppConfig(
        environment: AppEnvironment.production,
        apiBaseUrl: Uri.parse('https://api.example.test'),
        allowInsecureLocalHttp: false,
      );
      expect(config.apiBaseUrl.scheme, 'https');
    });

    test('rejects production HTTP even when flag is true', () {
      expect(
        () => AppConfig(
          environment: AppEnvironment.production,
          apiBaseUrl: Uri.parse('http://api.example.test'),
          allowInsecureLocalHttp: true,
        ),
        throwsA(isA<ConfigurationException>()),
      );
    });

    test('accepts explicit local emulator HTTP in development', () {
      final config = AppConfig(
        environment: AppEnvironment.development,
        apiBaseUrl: Uri.parse('http://10.0.2.2:8000'),
        allowInsecureLocalHttp: true,
      );
      expect(config.isDevelopment, isTrue);
    });

    test('rejects development HTTP without explicit opt in', () {
      expect(
        () => AppConfig(
          environment: AppEnvironment.development,
          apiBaseUrl: Uri.parse('http://127.0.0.1:8000'),
          allowInsecureLocalHttp: false,
        ),
        throwsA(isA<ConfigurationException>()),
      );
    });

    test('rejects public development HTTP host', () {
      expect(
        () => AppConfig(
          environment: AppEnvironment.development,
          apiBaseUrl: Uri.parse('http://example.test'),
          allowInsecureLocalHttp: true,
        ),
        throwsA(isA<ConfigurationException>()),
      );
    });

    test('rejects credentials and hidden API subpaths in base URL', () {
      for (final url in [
        'https://user:secret@api.example.test',
        'https://api.example.test/private-prefix',
      ]) {
        expect(
          () => AppConfig(
            environment: AppEnvironment.production,
            apiBaseUrl: Uri.parse(url),
            allowInsecureLocalHttp: false,
          ),
          throwsA(isA<ConfigurationException>()),
          reason: url,
        );
      }
    });
  });
}
