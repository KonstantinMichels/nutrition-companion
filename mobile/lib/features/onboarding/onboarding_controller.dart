import 'dart:async';

import 'package:flutter_riverpod/legacy.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../nutrition_assessment/assessment_repository.dart';
import '../profile/profile_repository.dart';
import '../privacy/privacy_repository.dart';
import 'draft_repository.dart';
import 'onboarding_models.dart';
import 'onboarding_validation.dart';

final onboardingControllerProvider =
    StateNotifierProvider<OnboardingController, OnboardingState>((ref) {
      return OnboardingController(
        ref.watch(draftRepositoryProvider),
        ref.watch(assessmentRepositoryProvider),
        ref.watch(profileRepositoryProvider),
        ref.watch(assessmentConsentStatusReaderProvider),
      );
    });

final class OnboardingState {
  const OnboardingState({
    required this.draft,
    this.initialized = false,
    this.submitting = false,
    this.hasActiveConsent = false,
    this.fieldErrors = const {},
    this.errorMessage,
    this.completedAssessmentId,
  });

  final OnboardingDraft draft;
  final bool initialized;
  final bool submitting;
  final bool hasActiveConsent;
  final Map<String, String> fieldErrors;
  final String? errorMessage;
  final String? completedAssessmentId;

  OnboardingState copyWith({
    OnboardingDraft? draft,
    bool? initialized,
    bool? submitting,
    bool? hasActiveConsent,
    Map<String, String>? fieldErrors,
    Object? errorMessage = _notSet,
    Object? completedAssessmentId = _notSet,
  }) => OnboardingState(
    draft: draft ?? this.draft,
    initialized: initialized ?? this.initialized,
    submitting: submitting ?? this.submitting,
    hasActiveConsent: hasActiveConsent ?? this.hasActiveConsent,
    fieldErrors: fieldErrors ?? this.fieldErrors,
    errorMessage: identical(errorMessage, _notSet)
        ? this.errorMessage
        : errorMessage as String?,
    completedAssessmentId: identical(completedAssessmentId, _notSet)
        ? this.completedAssessmentId
        : completedAssessmentId as String?,
  );
}

const _notSet = Object();

final class OnboardingController extends StateNotifier<OnboardingState> {
  OnboardingController(
    this._draftRepository,
    this._assessmentRepository,
    this._profileRepository,
    this._consentStatusReader,
  ) : super(OnboardingState(draft: OnboardingDraft.initial(DateTime.now())));

  final DraftRepository _draftRepository;
  final AssessmentRepository _assessmentRepository;
  final ProfileRepository _profileRepository;
  final AssessmentConsentStatusReader _consentStatusReader;
  Future<void> _saveTail = Future.value();

  Future<void> initialize({bool fresh = false}) async {
    if (state.initialized && !fresh) return;
    if (fresh) await _draftRepository.clear();
    final restored = fresh ? null : await _draftRepository.restore();
    if (restored != null) {
      state = OnboardingState(
        draft: restored,
        initialized: true,
        hasActiveConsent: await _consentStatusReader
            .hasActiveAssessmentConsent(),
      );
      return;
    }
    final stored = await _profileRepository.load();
    final draft = stored == null
        ? OnboardingDraft.initial(DateTime.now())
        : OnboardingDraft.fromStoredProfile(
            profile: stored.profile,
            activity: stored.activity,
            goal: stored.goal,
            restrictions: stored.restrictions,
            health: stored.health,
            now: DateTime.now(),
          );
    state = OnboardingState(
      draft: draft,
      initialized: true,
      hasActiveConsent:
          stored != null &&
          await _consentStatusReader.hasActiveAssessmentConsent(),
    );
    await _draftRepository.save(draft);
  }

  void updateField(String field, Object? value) {
    final updated = state.draft.withField(field, value, DateTime.now());
    final remainingErrors = Map<String, String>.from(state.fieldErrors)
      ..remove(field);
    state = state.copyWith(
      draft: updated,
      fieldErrors: remainingErrors,
      errorMessage: null,
    );
    _queueSave(updated);
  }

  void updateMeasurement(String field, MeasurementInput value) =>
      updateField(field, value.toJson());

  void setHealthFlag(String field, bool value) {
    final flags = Map<String, bool>.from(state.draft.healthFlags)
      ..[field] = value;
    updateField('health_flags', flags);
  }

  void addSport() {
    final updated = [
      ...state.draft.sports,
      SportInput(id: DateTime.now().microsecondsSinceEpoch.toString()),
    ];
    updateField('sports', updated.map((sport) => sport.toJson()).toList());
  }

  void updateSport(int index, SportInput sport) {
    final updated = [...state.draft.sports]..[index] = sport;
    updateField('sports', updated.map((entry) => entry.toJson()).toList());
  }

  void removeSport(int index) {
    final updated = [...state.draft.sports]..removeAt(index);
    updateField('sports', updated.map((sport) => sport.toJson()).toList());
  }

  bool next() {
    final errors = OnboardingValidation.validateStep(
      state.draft,
      state.draft.currentStep,
      hasActiveConsent: state.hasActiveConsent,
    );
    if (errors.isNotEmpty) {
      state = state.copyWith(fieldErrors: errors);
      return false;
    }
    jumpTo((state.draft.currentStep + 1).clamp(0, 9).toInt());
    return true;
  }

  void back() => jumpTo((state.draft.currentStep - 1).clamp(0, 9).toInt());

  void jumpTo(int step) {
    final updated = state.draft.withField('current_step', step, DateTime.now());
    state = state.copyWith(
      draft: updated,
      fieldErrors: const {},
      errorMessage: null,
    );
    _queueSave(updated);
  }

  Future<void> submit() async {
    if (state.submitting) return;
    final errors = OnboardingValidation.validateAll(
      state.draft,
      hasActiveConsent: state.hasActiveConsent,
    );
    if (errors.isNotEmpty) {
      state = state.copyWith(
        draft: state.draft.withField('current_step', 8, DateTime.now()),
        fieldErrors: errors,
        errorMessage: 'Bitte prüfe die markierten Angaben.',
      );
      return;
    }
    state = state.copyWith(
      submitting: true,
      errorMessage: null,
      fieldErrors: const {},
    );
    try {
      await _saveTail;
      final report = await _assessmentRepository.createFromDraft(state.draft);
      await _draftRepository.clear();
      state = state.copyWith(
        submitting: false,
        completedAssessmentId: report.summary.id,
      );
    } on AppException catch (error) {
      state = state.copyWith(
        submitting: false,
        errorMessage: error.message,
        fieldErrors: {
          for (final item in error.fieldErrors) item.field: item.message,
        },
      );
    } catch (_) {
      state = state.copyWith(
        submitting: false,
        errorMessage:
            'Die Einschätzung konnte nicht erstellt werden. Bitte versuche es erneut.',
      );
    }
  }

  Future<void> deleteDraft() async {
    await _draftRepository.clear();
    state = OnboardingState(
      draft: OnboardingDraft.initial(DateTime.now()),
      initialized: true,
    );
  }

  void _queueSave(OnboardingDraft value) {
    _saveTail = _saveTail
        .catchError((Object _) {})
        .then((_) => _draftRepository.save(value));
    unawaited(_saveTail);
  }
}
