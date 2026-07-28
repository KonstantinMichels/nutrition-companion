final class FieldError {
  const FieldError({
    required this.field,
    required this.code,
    required this.message,
  });

  final String field;
  final String code;
  final String message;

  factory FieldError.fromJson(Map<String, dynamic> json) => FieldError(
    field: json['field']?.toString() ?? '',
    code: json['code']?.toString() ?? 'INVALID',
    message: json['message']?.toString() ?? 'Ungültige Eingabe.',
  );
}

class AppException implements Exception {
  const AppException(
    this.message, {
    this.code = 'UNKNOWN',
    this.fieldErrors = const [],
  });

  final String message;
  final String code;
  final List<FieldError> fieldErrors;

  @override
  String toString() => message;
}

final class NetworkException extends AppException {
  const NetworkException(super.message, {super.code = 'NETWORK_ERROR'});
}

final class ApiException extends AppException {
  const ApiException(
    super.message, {
    required this.statusCode,
    super.code = 'API_ERROR',
    super.fieldErrors,
  });

  final int? statusCode;
}
