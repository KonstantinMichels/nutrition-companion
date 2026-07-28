import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../core/secure_storage/sensitive_store.dart';
import '../features/nutrition_assessment/assessment_repository.dart';
import '../features/onboarding/draft_repository.dart';

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
