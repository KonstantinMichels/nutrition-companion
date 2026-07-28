import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../errors/app_exception.dart';

final class ApiClient {
  ApiClient(AppConfig config, {Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: config.apiBaseUrl.toString().replaceFirst(
                RegExp(r'/$'),
                '',
              ),
              connectTimeout: config.connectTimeout,
              receiveTimeout: config.receiveTimeout,
              sendTimeout: config.receiveTimeout,
              headers: const {'Accept': 'application/json'},
              contentType: Headers.jsonContentType,
            ),
          );

  final Dio _dio;

  Future<bool> health() async {
    try {
      final response = await _dio.get<dynamic>('/health');
      return response.statusCode == 200;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<dynamic> get(String path) async {
    try {
      return (await _dio.get<dynamic>(path)).data;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<dynamic> post(String path, {Object? data}) async {
    try {
      return (await _dio.post<dynamic>(path, data: data)).data;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<dynamic> put(String path, {Object? data}) async {
    try {
      return (await _dio.put<dynamic>(path, data: data)).data;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<dynamic> delete(String path, {Object? data}) async {
    try {
      return (await _dio.delete<dynamic>(path, data: data)).data;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  AppException _mapError(DioException error) {
    final response = error.response;
    if (response == null) {
      final message = switch (error.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout =>
          'Die Anfrage hat zu lange gedauert. Bitte versuche es erneut.',
        DioExceptionType.connectionError =>
          'Der Server ist nicht erreichbar. Prüfe deine Verbindung.',
        _ => 'Es ist ein Verbindungsfehler aufgetreten.',
      };
      return NetworkException(message, code: error.type.name.toUpperCase());
    }

    final body = response.data;
    Map<String, dynamic>? envelope;
    if (body is Map) {
      final normalized = Map<String, dynamic>.from(body);
      final rawError = normalized['error'];
      envelope = rawError is Map
          ? Map<String, dynamic>.from(rawError)
          : normalized;
    }
    final rawFields = envelope?['field_errors'];
    final fields = rawFields is List
        ? rawFields
              .whereType<Map>()
              .map(
                (item) => FieldError.fromJson(Map<String, dynamic>.from(item)),
              )
              .toList(growable: false)
        : const <FieldError>[];
    return ApiException(
      envelope?['message']?.toString() ?? _statusMessage(response.statusCode),
      statusCode: response.statusCode,
      code: envelope?['code']?.toString() ?? 'HTTP_${response.statusCode ?? 0}',
      fieldErrors: fields,
    );
  }

  static String _statusMessage(int? status) => switch (status) {
    400 || 422 => 'Die Eingaben konnten nicht verarbeitet werden.',
    401 || 403 => 'Diese Aktion ist nicht erlaubt.',
    404 => 'Die angeforderten Daten wurden nicht gefunden.',
    409 => 'Die Aktion konnte wegen eines Konflikts nicht ausgeführt werden.',
    _ => 'Der Server konnte die Anfrage nicht verarbeiten.',
  };
}
