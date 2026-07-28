import 'dart:convert';

import '../../core/api/api_client.dart';
import '../../core/errors/app_exception.dart';
import '../../core/secure_storage/sensitive_store.dart';
import '../onboarding/onboarding_models.dart';
import 'assessment_models.dart';

final class AssessmentRepository {
  const AssessmentRepository(this._api, this._store);

  final ApiClient _api;
  final SensitiveStore _store;

  Future<AssessmentReport?> latest() async {
    try {
      final raw = await _api.get('/api/v1/assessments/latest');
      if (raw is! Map) throw const AppException('Ungültige Serverantwort.');
      final report = AssessmentReport.fromJson(Map<String, dynamic>.from(raw));
      await cacheSummary(report.summary);
      return report;
    } on ApiException catch (error) {
      if (error.statusCode == 404) {
        await clearCache();
        return null;
      }
      rethrow;
    }
  }

  Future<AssessmentReport> getById(String id) async {
    final raw = await _api.get('/api/v1/assessments/$id');
    if (raw is! Map) throw const AppException('Ungültige Serverantwort.');
    return AssessmentReport.fromJson(Map<String, dynamic>.from(raw));
  }

  Future<List<AssessmentSummary>> history() async {
    final raw = await _api.get('/api/v1/assessments');
    final body = raw is Map
        ? Map<String, dynamic>.from(raw)
        : <String, dynamic>{};
    final items = raw is List ? raw : body['items'];
    if (items is! List) return const [];
    return items
        .whereType<Map>()
        .map(
          (item) => AssessmentSummary.fromHistoryJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList(growable: false);
  }

  Future<AssessmentReport> createFromDraft(OnboardingDraft draft) async {
    // The profile sections deliberately use their typed endpoints. Repeating the
    // PUTs during retry is safe; client_request_id makes assessment creation
    // idempotent after a lost response.
    await _api.put('/api/v1/profile', data: draft.profileRequest());
    await _api.put('/api/v1/profile/activity', data: draft.activityRequest());
    await _api.put('/api/v1/profile/goal', data: draft.goalRequest());
    await _api.put(
      '/api/v1/profile/restrictions',
      data: {'restrictions': draft.restrictionRequest()},
    );
    await _api.put(
      '/api/v1/profile/health-screening',
      data: draft.healthRequest(),
    );
    final consentResponse = await _api.get('/api/v1/privacy/consents');
    final existingConsents = consentResponse is List
        ? consentResponse
        : const [];
    final hasMatchingConsent = existingConsents.whereType<Map>().any(
      (item) =>
          item['purpose_code'] == 'nutrition_assessment_calculation' &&
          item['consent_text_version'] == draft.consentTextVersion &&
          item['status'] == 'granted',
    );
    if (!hasMatchingConsent) {
      if (!draft.consentAccepted) {
        throw const AppException(
          'Ohne aktive oder erneut ausdrücklich erteilte Einwilligung kann keine Auswertung erstellt werden.',
        );
      }
      await _api.post('/api/v1/privacy/consents', data: draft.consentRequest());
    }
    final raw = await _api.post(
      '/api/v1/assessments',
      data: {'client_request_id': draft.clientRequestId},
    );
    if (raw is! Map) throw const AppException('Ungültige Serverantwort.');
    final report = AssessmentReport.fromJson(Map<String, dynamic>.from(raw));
    await cacheSummary(report.summary);
    return report;
  }

  Future<void> cacheSummary(AssessmentSummary summary) => _store.write(
    SensitiveKeys.latestAssessment,
    jsonEncode({
      'cached_at': DateTime.now().toUtc().toIso8601String(),
      'summary': summary.toJson(),
    }),
  );

  Future<CachedAssessment?> cachedLatest() async {
    final raw = await _store.read(SensitiveKeys.latestAssessment);
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw);
      if (json is! Map) throw const FormatException();
      final normalized = Map<String, dynamic>.from(json);
      final summary = normalized['summary'];
      if (summary is! Map) throw const FormatException();
      return CachedAssessment(
        summary: AssessmentSummary.fromJson(Map<String, dynamic>.from(summary)),
        cachedAt: DateTime.parse(normalized['cached_at'].toString()),
      );
    } on FormatException {
      await clearCache();
      return null;
    } on TypeError {
      await clearCache();
      return null;
    }
  }

  Future<void> clearCache() => _store.delete(SensitiveKeys.latestAssessment);

  Future<void> deleteHistory() async {
    await _api.delete('/api/v1/assessments', data: {'confirm': true});
    await clearCache();
  }
}
