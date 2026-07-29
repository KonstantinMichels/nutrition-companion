import 'dart:convert';

import '../../core/secure_storage/sensitive_store.dart';

final class DailyPlanDraftRepository {
  const DailyPlanDraftRepository(this._store);
  final SensitiveStore _store;
  static const expiry = Duration(days: 30);

  Future<Map<String, dynamic>?> read(String date) async {
    final raw = await _store.read(SensitiveKeys.dailyPlanDrafts);
    if (raw == null) return null;
    final all = Map<String, dynamic>.from(jsonDecode(raw) as Map);
    final value = all[date];
    if (value is! Map) return null;
    final savedAt = DateTime.tryParse(value['saved_at']?.toString() ?? '');
    if (savedAt == null || DateTime.now().difference(savedAt) > expiry) {
      all.remove(date);
      await _writeAll(all);
      return null;
    }
    return Map<String, dynamic>.from(value['payload'] as Map);
  }

  Future<void> write(String date, Map<String, dynamic> payload) async {
    final raw = await _store.read(SensitiveKeys.dailyPlanDrafts);
    final all = raw == null
        ? <String, dynamic>{}
        : Map<String, dynamic>.from(jsonDecode(raw) as Map);
    all[date] = {
      'saved_at': DateTime.now().toUtc().toIso8601String(),
      'payload': payload,
    };
    await _writeAll(all);
  }

  Future<void> delete(String date) async {
    final raw = await _store.read(SensitiveKeys.dailyPlanDrafts);
    if (raw == null) return;
    final all = Map<String, dynamic>.from(jsonDecode(raw) as Map)..remove(date);
    await _writeAll(all);
  }

  Future<void> _writeAll(Map<String, dynamic> all) => all.isEmpty
      ? _store.delete(SensitiveKeys.dailyPlanDrafts)
      : _store.write(SensitiveKeys.dailyPlanDrafts, jsonEncode(all));
}
