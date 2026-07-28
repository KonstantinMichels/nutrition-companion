import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/settings/theme_controller.dart';
import 'branding.dart';
import 'router.dart';
import 'theme.dart';

final class NutritionCompanionApp extends ConsumerWidget {
  const NutritionCompanionApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
    title: AppBranding.productName,
    debugShowCheckedModeBanner: false,
    theme: AppTheme.light(),
    darkTheme: AppTheme.dark(),
    themeMode: ref.watch(themeControllerProvider),
    locale: const Locale('de', 'DE'),
    supportedLocales: const [Locale('de', 'DE')],
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    routerConfig: appRouter,
  );
}

final class ConfigurationErrorApp extends StatelessWidget {
  const ConfigurationErrorApp({required this.message, super.key});
  final String message;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: AppBranding.productName,
    theme: AppTheme.light(),
    home: Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.settings_outlined, size: 64),
                const SizedBox(height: 16),
                const Text(
                  'Die App-Konfiguration ist ungültig.',
                  style: TextStyle(fontSize: 20),
                ),
                const SizedBox(height: 12),
                SelectableText(message, textAlign: TextAlign.center),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
