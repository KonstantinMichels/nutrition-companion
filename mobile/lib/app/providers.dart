import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../core/secure_storage/sensitive_store.dart';
import '../features/nutrition_assessment/assessment_repository.dart';
import '../features/onboarding/draft_repository.dart';
import '../features/foods/food_repository.dart';
import '../features/recipes/recipe_repository.dart';
import '../features/recipes/recipe_comparison_repository.dart';
import '../features/recipes/recipe_availability_repository.dart';
import '../features/daily_plans/daily_plan_draft_repository.dart';
import '../features/daily_plans/daily_plan_repository.dart';
import '../features/weekly_plans/weekly_plan_repository.dart';
import '../features/pantry/pantry_repository.dart';
import '../features/shopping_lists/shopping_list_repository.dart';
import '../features/shopping_lists/pantry_aware_shopping_repository.dart';

final appConfigProvider = Provider<AppConfig>(
  (ref) => throw StateError('AppConfig was not supplied at startup.'),
);

final sensitiveStoreProvider = Provider<SensitiveStore>(
  (ref) => FlutterSensitiveStore(),
);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(ref.watch(appConfigProvider)),
);

final draftRepositoryProvider = Provider<DraftRepository>(
  (ref) => DraftRepository(ref.watch(sensitiveStoreProvider)),
);

final assessmentRepositoryProvider = Provider<AssessmentRepository>(
  (ref) => AssessmentRepository(
    ref.watch(apiClientProvider),
    ref.watch(sensitiveStoreProvider),
  ),
);

final foodRepositoryProvider = Provider<FoodRepository>(
  (ref) => FoodRepository(ref.watch(apiClientProvider)),
);

final recipeRepositoryProvider = Provider<RecipeRepository>(
  (ref) => RecipeRepository(ref.watch(apiClientProvider)),
);

final recipeComparisonRepositoryProvider = Provider<RecipeComparisonRepository>(
  (ref) => RecipeComparisonRepository(ref.watch(apiClientProvider)),
);

final recipeAvailabilityRepositoryProvider =
    Provider<RecipeAvailabilityRepository>(
      (ref) => RecipeAvailabilityRepository(ref.watch(apiClientProvider)),
    );

final dailyPlanRepositoryProvider = Provider<DailyPlanRepository>(
  (ref) => DailyPlanRepository(ref.watch(apiClientProvider)),
);

final dailyPlanDraftRepositoryProvider = Provider<DailyPlanDraftRepository>(
  (ref) => DailyPlanDraftRepository(ref.watch(sensitiveStoreProvider)),
);

final weeklyPlanRepositoryProvider = Provider<WeeklyPlanRepository>(
  (ref) => WeeklyPlanRepository(ref.watch(apiClientProvider)),
);

final pantryRepositoryProvider = Provider<PantryRepository>(
  (ref) => PantryRepository(ref.watch(apiClientProvider)),
);

final shoppingListRepositoryProvider = Provider<ShoppingListRepository>(
  (ref) => ShoppingListRepository(ref.watch(apiClientProvider)),
);

final pantryAwareShoppingRepositoryProvider =
    Provider<PantryAwareShoppingRepository>(
      (ref) => PantryAwareShoppingRepository(ref.watch(apiClientProvider)),
    );
