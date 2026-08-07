import '../../core/api/api_client.dart';

final class PantryReconciliationRepository {
  PantryReconciliationRepository(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>> statusForDay(String dayId) async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/consumption-days/$dayId/pantry-reconciliation')
            as Map,
      );

  Future<Map<String, dynamic>> preview(
    String dayId,
    Map<String, dynamic> request,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/pantry-reconciliation/preview',
          data: request,
        )
        as Map,
  );

  Future<Map<String, dynamic>> apply(
    String dayId,
    Map<String, dynamic> request,
    String token,
    String operationId,
    List<String> dateConfirmations,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/pantry-reconciliation/apply',
          data: {
            'client_operation_id': operationId,
            'preview_token': token,
            'preview': request,
            'past_use_by_confirmations': dateConfirmations,
          },
        )
        as Map,
  );

  Future<Map<String, dynamic>> history({String? dayId}) async =>
      Map<String, dynamic>.from(
        await _api.get(
              '/api/v1/pantry-consumption-reconciliations'
              '${dayId == null ? '' : '?consumption_day_id=$dayId'}',
            )
            as Map,
      );

  Future<Map<String, dynamic>> reversalPreview(
    String batchId,
    Map<String, dynamic> request,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/pantry-consumption-reconciliations/$batchId/reversal-preview',
          data: request,
        )
        as Map,
  );

  Future<Map<String, dynamic>> reverse(
    String batchId,
    Map<String, dynamic> request,
    String token,
    String operationId,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/pantry-consumption-reconciliations/$batchId/reverse',
          data: {
            'client_operation_id': operationId,
            'preview_token': token,
            'preview': request,
          },
        )
        as Map,
  );

  Future<Map<String, dynamic>> deletionPreview(
    String dayId, {
    String? entryId,
  }) async => Map<String, dynamic>.from(
    await _api.get(
          entryId == null
              ? '/api/v1/consumption-days/$dayId/pantry-reconciliation/deletion-preview'
              : '/api/v1/consumption-days/$dayId/entries/$entryId/pantry-reconciliation/deletion-preview',
        )
        as Map,
  );

  Future<Map<String, dynamic>> deleteWithResolution(
    String dayId, {
    String? entryId,
    required String policy,
    String? operationId,
  }) async => Map<String, dynamic>.from(
    await _api.post(
          entryId == null
              ? '/api/v1/consumption-days/$dayId/pantry-reconciliation/delete-with-resolution'
              : '/api/v1/consumption-days/$dayId/entries/$entryId/pantry-reconciliation/delete-with-resolution',
          data: {'policy': policy, 'client_operation_id': ?operationId},
        )
        as Map,
  );
}
