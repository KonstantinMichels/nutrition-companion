import 'package:nutrition_companion/core/secure_storage/sensitive_store.dart';

final class FakeSensitiveStore implements SensitiveStore {
  final values = <String, String>{};

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async => values[key] = value;

  @override
  Future<void> delete(String key) async => values.remove(key);

  @override
  Future<void> clearAppData() async {
    for (final key in SensitiveKeys.values) {
      values.remove(key);
    }
  }
}
