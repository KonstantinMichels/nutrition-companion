import 'package:flutter_riverpod/legacy.dart';

import '../../app/providers.dart';
import '../nutrition_assessment/assessment_models.dart';
import '../nutrition_assessment/assessment_repository.dart';

final homeControllerProvider = StateNotifierProvider<HomeController, HomeState>(
  (ref) {
    final controller = HomeController(ref.watch(assessmentRepositoryProvider));
    controller.load();
    return controller;
  },
);

final class HomeState {
  const HomeState({
    this.loading = true,
    this.summary,
    this.cached = false,
    this.stale = false,
    this.message,
  });

  final bool loading;
  final AssessmentSummary? summary;
  final bool cached;
  final bool stale;
  final String? message;
}

final class HomeController extends StateNotifier<HomeState> {
  HomeController(this._repository) : super(const HomeState());

  final AssessmentRepository _repository;

  Future<void> load() async {
    state = HomeState(
      loading: true,
      summary: state.summary,
      cached: state.cached,
    );
    try {
      final report = await _repository.latest();
      state = HomeState(loading: false, summary: report?.summary);
    } catch (_) {
      final cached = await _repository.cachedLatest();
      final stale = cached?.isStale(DateTime.now()) ?? false;
      state = HomeState(
        loading: false,
        summary: cached?.summary,
        cached: cached != null,
        stale: stale,
        message: cached == null
            ? 'Der Server ist derzeit nicht erreichbar.'
            : stale
            ? 'Offline: Die lokale Zusammenfassung ist älter als 24 Stunden und möglicherweise veraltet.'
            : 'Offline: Es wird die zuletzt sicher gespeicherte Zusammenfassung angezeigt.',
      );
    }
  }
}
