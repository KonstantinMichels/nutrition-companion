import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'app/app.dart';
import 'app/providers.dart';
import 'core/config/app_config.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  Intl.defaultLocale = 'de_DE';
  try {
    final config = AppConfig.fromEnvironment();
    runApp(
      ProviderScope(
        overrides: [appConfigProvider.overrideWithValue(config)],
        child: const NutritionCompanionApp(),
      ),
    );
  } on ConfigurationException catch (error) {
    runApp(ConfigurationErrorApp(message: error.message));
  }
}
