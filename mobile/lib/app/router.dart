import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/assessment_history/history_screen.dart';
import '../features/assessment_results/assessment_report_screen.dart';
import '../features/bootstrap/bootstrap_screen.dart';
import '../features/home/home_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/privacy/privacy_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/foods/food_list_screen.dart';
import '../features/foods/food_detail_screen.dart';
import '../features/foods/food_form_screen.dart';
import '../features/foods/barcode_scanner_screen.dart';
import '../features/recipes/recipe_detail_screen.dart';
import '../features/recipes/recipe_form_screen.dart';
import '../features/recipes/recipe_list_screen.dart';
import '../features/daily_plans/daily_plan_editor_screen.dart';
import '../features/daily_plans/daily_plan_screen.dart';
import '../features/weekly_plans/weekly_plan_screen.dart';
import '../features/pantry/pantry_add_screen.dart';
import '../features/pantry/pantry_detail_screen.dart';
import '../features/pantry/pantry_locations_screen.dart';
import '../features/pantry/pantry_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const BootstrapScreen()),
    GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
    GoRoute(path: '/pantry', builder: (context, state) => const PantryScreen()),
    GoRoute(
      path: '/pantry/add',
      builder: (context, state) => const PantryAddScreen(),
    ),
    GoRoute(
      path: '/pantry/locations',
      builder: (context, state) => const PantryLocationsScreen(),
    ),
    GoRoute(
      path: '/pantry/items/:id',
      builder: (context, state) =>
          PantryDetailScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/weekly-plan',
      builder: (context, state) => const WeeklyPlanScreen(),
    ),
    GoRoute(
      path: '/daily-plan',
      builder: (context, state) => DailyPlanScreen(
        initialDate: DateTime.tryParse(state.uri.queryParameters['date'] ?? ''),
      ),
    ),
    GoRoute(
      path: '/daily-plan/edit',
      builder: (context, state) => DailyPlanEditorScreen(
        id: state.uri.queryParameters['id'],
        returnToWeeklyPlan:
            state.uri.queryParameters['returnTo'] == 'weekly-plan',
        date:
            DateTime.tryParse(state.uri.queryParameters['date'] ?? '') ??
            DateTime.now(),
      ),
    ),
    GoRoute(
      path: '/onboarding',
      builder: (context, state) =>
          OnboardingScreen(fresh: state.uri.queryParameters['new'] == 'true'),
    ),
    GoRoute(
      path: '/assessment/:id',
      builder: (context, state) =>
          AssessmentReportScreen(assessmentId: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/history',
      builder: (context, state) => const HistoryScreen(),
    ),
    GoRoute(
      path: '/profile',
      builder: (context, state) => const ProfileScreen(),
    ),
    GoRoute(
      path: '/privacy',
      builder: (context, state) => const PrivacyScreen(),
    ),
    GoRoute(
      path: '/settings',
      builder: (context, state) => const SettingsScreen(),
    ),
    GoRoute(
      path: '/foods',
      builder: (context, state) => const FoodListScreen(),
    ),
    GoRoute(
      path: '/foods/new',
      builder: (context, state) => const FoodFormScreen(),
    ),
    GoRoute(
      path: '/foods/scan',
      builder: (context, state) => const BarcodeScannerScreen(),
    ),
    GoRoute(
      path: '/foods/:id',
      builder: (context, state) =>
          FoodDetailScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/foods/:id/edit',
      builder: (context, state) =>
          FoodFormScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/recipes',
      builder: (context, state) => const RecipeListScreen(),
    ),
    GoRoute(
      path: '/recipes/new',
      builder: (context, state) =>
          RecipeFormScreen(initialFoodId: state.uri.queryParameters['foodId']),
    ),
    GoRoute(
      path: '/recipes/:id',
      builder: (context, state) =>
          RecipeDetailScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(
      path: '/recipes/:id/edit',
      builder: (context, state) =>
          RecipeFormScreen(id: state.pathParameters['id']!),
    ),
  ],
  errorBuilder: (context, state) => Scaffold(
    appBar: AppBar(title: const Text('Seite nicht gefunden')),
    body: Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Diese Seite konnte nicht geöffnet werden.'),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => context.go('/home'),
              child: const Text('Zur Übersicht'),
            ),
          ],
        ),
      ),
    ),
  ),
);
