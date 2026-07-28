import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/branding.dart';
import '../../app/providers.dart';
import '../../core/api/api_client.dart';
import '../../core/errors/app_exception.dart';
import '../../core/secure_storage/sensitive_store.dart';

final privacyRepositoryProvider = Provider<PrivacyRepository>(
  (ref) => PrivacyRepository(
    ref.watch(apiClientProvider),
    ref.watch(sensitiveStoreProvider),
  ),
);

final consentsProvider = FutureProvider<List<ConsentRecord>>(
  (ref) => ref.watch(privacyRepositoryProvider).consents(),
);

abstract interface class AssessmentConsentStatusReader {
  Future<bool> hasActiveAssessmentConsent();
}

final assessmentConsentStatusReaderProvider =
    Provider<AssessmentConsentStatusReader>(
      (ref) => ref.watch(privacyRepositoryProvider),
    );

final class ConsentRecord {
  const ConsentRecord({
    required this.id,
    required this.purposeCode,
    required this.textVersion,
    required this.status,
    required this.grantedAt,
    required this.withdrawnAt,
    required this.source,
  });

  final String id;
  final String purposeCode;
  final String textVersion;
  final String status;
  final DateTime? grantedAt;
  final DateTime? withdrawnAt;
  final String source;

  factory ConsentRecord.fromJson(Map<String, dynamic> json) => ConsentRecord(
    id: json['id']?.toString() ?? '',
    purposeCode: json['purpose_code']?.toString() ?? '',
    textVersion: json['consent_text_version']?.toString() ?? '',
    status: json['status']?.toString() ?? 'unknown',
    grantedAt: DateTime.tryParse(json['granted_at']?.toString() ?? ''),
    withdrawnAt: DateTime.tryParse(json['withdrawn_at']?.toString() ?? ''),
    source: json['source']?.toString() ?? '',
  );
}

final class PrivacyRepository implements AssessmentConsentStatusReader {
  const PrivacyRepository(this._api, this._store);
  final ApiClient _api;
  final SensitiveStore _store;

  Future<List<ConsentRecord>> consents() async {
    final raw = await _api.get('/api/v1/privacy/consents');
    final envelope = raw is Map
        ? Map<String, dynamic>.from(raw)
        : <String, dynamic>{};
    final items = raw is List ? raw : envelope['items'] ?? envelope['consents'];
    if (items is! List) return const [];
    return items
        .whereType<Map>()
        .map((item) => ConsentRecord.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }

  @override
  Future<bool> hasActiveAssessmentConsent() async {
    try {
      final records = await consents();
      return records.any(
        (record) =>
            record.purposeCode == AppBranding.consentPurpose &&
            record.textVersion == AppBranding.consentTextVersion &&
            record.status == 'granted' &&
            record.withdrawnAt == null,
      );
    } on ApiException catch (error) {
      if (error.statusCode == 404) return false;
      rethrow;
    }
  }

  Future<void> withdraw(String consentId) async {
    await _api.post('/api/v1/privacy/consents/$consentId/withdraw');
  }

  Future<void> exportAndShare() async {
    final export = await _api.get('/api/v1/privacy/export');
    final directory = await getTemporaryDirectory();
    final file = File(
      '${directory.path}/nutrition-companion-export-${DateTime.now().millisecondsSinceEpoch}.json',
    );
    try {
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(export),
        flush: true,
      );
      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path, mimeType: 'application/json')],
          subject: '${AppBranding.productName} – Datenexport',
          text: 'Dieser Export wurde auf deine ausdrückliche Aktion erstellt.',
        ),
      );
    } finally {
      if (await file.exists()) await file.delete();
      await deleteSharePlusCache(directory);
    }
  }

  Future<void> deleteHistory() async {
    await _api.delete('/api/v1/assessments', data: {'confirm': true});
    await clearCache();
  }

  Future<void> deleteProfile() async {
    try {
      await _api.delete('/api/v1/profile', data: {'confirm': true});
    } on ApiException catch (error) {
      // A previous successful server deletion followed by a local key-store
      // failure must still be recoverable on retry.
      if (error.statusCode != 404) rethrow;
    }
    await _store.clearAppData();
  }

  Future<void> clearDraft() => _store.delete(SensitiveKeys.onboardingDraft);
  Future<void> clearCache() => _store.delete(SensitiveKeys.latestAssessment);
}

Future<void> deleteSharePlusCache(Directory temporaryDirectory) async {
  final shareCache = Directory('${temporaryDirectory.path}/share_plus');
  if (await shareCache.exists()) {
    await shareCache.delete(recursive: true);
  }
}
