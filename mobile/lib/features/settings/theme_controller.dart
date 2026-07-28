import 'package:flutter/material.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:shared_preferences/shared_preferences.dart';

final themeControllerProvider =
    StateNotifierProvider<ThemeController, ThemeMode>(
      (ref) => ThemeController()..load(),
    );

final class ThemeController extends StateNotifier<ThemeMode> {
  ThemeController({Future<SharedPreferences> Function()? preferences})
    : _preferences = preferences ?? SharedPreferences.getInstance,
      super(ThemeMode.system);

  static const _key = 'ui.theme_mode';
  final Future<SharedPreferences> Function() _preferences;

  Future<void> load() async {
    final value = (await _preferences()).getString(_key);
    state = switch (value) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
  }

  Future<void> setTheme(ThemeMode mode) async {
    state = mode;
    await (await _preferences()).setString(_key, mode.name);
  }
}
