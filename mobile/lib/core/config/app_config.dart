enum AppEnvironment { development, staging, production }

final class ConfigurationException implements Exception {
  const ConfigurationException(this.message);
  final String message;

  @override
  String toString() => 'ConfigurationException: $message';
}

final class AppConfig {
  AppConfig({
    required this.environment,
    required this.apiBaseUrl,
    required this.allowInsecureLocalHttp,
    this.connectTimeout = const Duration(seconds: 10),
    this.receiveTimeout = const Duration(seconds: 20),
  }) {
    _validate();
  }

  factory AppConfig.fromEnvironment() {
    const environmentValue = String.fromEnvironment(
      'APP_ENV',
      defaultValue: 'development',
    );
    final environment = switch (environmentValue.toLowerCase()) {
      'production' || 'prod' => AppEnvironment.production,
      'staging' => AppEnvironment.staging,
      'development' || 'dev' => AppEnvironment.development,
      _ => throw ConfigurationException(
        'Unbekannter APP_ENV-Wert: $environmentValue',
      ),
    };

    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000',
    );
    const allowHttp = bool.fromEnvironment(
      'ALLOW_INSECURE_LOCAL_HTTP',
      defaultValue: false,
    );

    return AppConfig(
      environment: environment,
      apiBaseUrl: Uri.parse(baseUrl),
      allowInsecureLocalHttp: allowHttp,
    );
  }

  final AppEnvironment environment;
  final Uri apiBaseUrl;
  final bool allowInsecureLocalHttp;
  final Duration connectTimeout;
  final Duration receiveTimeout;

  bool get isDevelopment => environment == AppEnvironment.development;

  void _validate() {
    if (!apiBaseUrl.hasScheme || apiBaseUrl.host.isEmpty) {
      throw const ConfigurationException(
        'API_BASE_URL muss eine vollständige URL sein.',
      );
    }
    if (apiBaseUrl.hasQuery || apiBaseUrl.hasFragment) {
      throw const ConfigurationException(
        'API_BASE_URL darf keine Query oder Fragment enthalten.',
      );
    }
    if (apiBaseUrl.userInfo.isNotEmpty ||
        (apiBaseUrl.path.isNotEmpty && apiBaseUrl.path != '/')) {
      throw const ConfigurationException(
        'API_BASE_URL darf keine Zugangsdaten oder Unterpfade enthalten.',
      );
    }
    if (apiBaseUrl.scheme == 'https') return;
    if (apiBaseUrl.scheme != 'http') {
      throw const ConfigurationException(
        'Nur HTTPS und lokales HTTP sind erlaubt.',
      );
    }
    if (environment != AppEnvironment.development ||
        !allowInsecureLocalHttp ||
        !_isLocalDevelopmentHost(apiBaseUrl.host)) {
      throw const ConfigurationException(
        'HTTP ist ausschließlich im explizit aktivierten lokalen Entwicklungsmodus erlaubt.',
      );
    }
  }

  static bool _isLocalDevelopmentHost(String host) {
    if (host == 'localhost' || host == '127.0.0.1' || host == '10.0.2.2') {
      return true;
    }
    final parts = host.split('.').map(int.tryParse).toList(growable: false);
    if (parts.length != 4 ||
        parts.any((part) => part == null || part < 0 || part > 255)) {
      return false;
    }
    final a = parts[0]!;
    final b = parts[1]!;
    return a == 10 ||
        (a == 192 && b == 168) ||
        (a == 172 && b >= 16 && b <= 31);
  }
}
