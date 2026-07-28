import 'dart:math';

import '../../app/branding.dart';
import '../../core/formatting/german_decimal.dart';

const _unset = Object();

final class MeasurementInput {
  const MeasurementInput({
    this.value = '',
    this.measuredAt,
    this.sourceType = 'measured',
  });

  final String value;
  final DateTime? measuredAt;
  final String sourceType;

  bool get isEmpty => value.trim().isEmpty;

  MeasurementInput copyWith({
    String? value,
    Object? measuredAt = _unset,
    String? sourceType,
  }) => MeasurementInput(
    value: value ?? this.value,
    measuredAt: identical(measuredAt, _unset)
        ? this.measuredAt
        : measuredAt as DateTime?,
    sourceType: sourceType ?? this.sourceType,
  );

  Map<String, dynamic> toJson() => {
    'value': value,
    'measured_at': measuredAt?.toIso8601String(),
    'source_type': sourceType,
  };

  factory MeasurementInput.fromJson(Object? raw) {
    if (raw is! Map) return const MeasurementInput();
    final json = Map<String, dynamic>.from(raw);
    return MeasurementInput(
      value: json['value']?.toString() ?? '',
      measuredAt: DateTime.tryParse(json['measured_at']?.toString() ?? ''),
      sourceType: json['source_type']?.toString() ?? 'measured',
    );
  }
}

final class SportInput {
  const SportInput({
    required this.id,
    this.sportType = 'strength_training',
    this.sessionsPerWeek = '1',
    this.minutesPerSession = '45',
    this.intensity = 'moderate',
    this.note = '',
  });

  final String id;
  final String sportType;
  final String sessionsPerWeek;
  final String minutesPerSession;
  final String intensity;
  final String note;

  SportInput copyWith({
    String? sportType,
    String? sessionsPerWeek,
    String? minutesPerSession,
    String? intensity,
    String? note,
  }) => SportInput(
    id: id,
    sportType: sportType ?? this.sportType,
    sessionsPerWeek: sessionsPerWeek ?? this.sessionsPerWeek,
    minutesPerSession: minutesPerSession ?? this.minutesPerSession,
    intensity: intensity ?? this.intensity,
    note: note ?? this.note,
  );

  double get weeklyMinutes =>
      (GermanDecimal.tryParse(sessionsPerWeek) ?? 0) *
      (GermanDecimal.tryParse(minutesPerSession) ?? 0);

  Map<String, dynamic> toJson() => {
    'id': id,
    'sport_type': sportType,
    'sessions_per_week': sessionsPerWeek,
    'minutes_per_session': minutesPerSession,
    'intensity': intensity,
    'note': note,
  };

  Map<String, dynamic> toApiJson() => {
    'sport_type': sportType,
    'sessions_per_week': GermanDecimal.parse(sessionsPerWeek),
    'minutes_per_session': GermanDecimal.parse(minutesPerSession).round(),
    'intensity': intensity,
    if (note.trim().isNotEmpty) 'note': note.trim(),
  };

  factory SportInput.fromJson(Object? raw) {
    final json = raw is Map
        ? Map<String, dynamic>.from(raw)
        : <String, dynamic>{};
    return SportInput(
      id:
          json['id']?.toString() ??
          DateTime.now().microsecondsSinceEpoch.toString(),
      sportType: json['sport_type']?.toString() ?? 'strength_training',
      sessionsPerWeek: json['sessions_per_week']?.toString() ?? '1',
      minutesPerSession: json['minutes_per_session']?.toString() ?? '45',
      intensity: json['intensity']?.toString() ?? 'moderate',
      note: json['note']?.toString() ?? '',
    );
  }
}

final class OnboardingDraft {
  const OnboardingDraft({
    required this.schemaVersion,
    required this.currentStep,
    required this.startedAt,
    required this.updatedAt,
    required this.clientRequestId,
    required this.goalType,
    required this.targetWeightKg,
    required this.desiredIntensity,
    required this.requestedWeeklyRateKg,
    required this.birthDate,
    required this.heightCm,
    required this.weightKg,
    required this.physiologicalCategory,
    required this.measuredRee,
    required this.bodyFat,
    required this.waist,
    required this.hip,
    required this.occupationalActivity,
    required this.averageSteps,
    required this.activeCommuting,
    required this.movementNote,
    required this.manualPalOverride,
    required this.sports,
    required this.dietaryPreference,
    required this.allergies,
    required this.intolerances,
    required this.excludedFoods,
    required this.dislikedFoods,
    required this.preferredMeals,
    required this.mealTiming,
    required this.healthFlags,
    required this.healthNote,
    required this.consentAccepted,
    required this.consentTextVersion,
  });

  factory OnboardingDraft.initial(DateTime now) => OnboardingDraft(
    schemaVersion: 1,
    currentStep: 0,
    startedAt: now.toUtc(),
    updatedAt: now.toUtc(),
    clientRequestId: _uuidV4(),
    goalType: '',
    targetWeightKg: '',
    desiredIntensity: 'mild',
    requestedWeeklyRateKg: '',
    birthDate: '',
    heightCm: '',
    weightKg: '',
    physiologicalCategory: '',
    measuredRee: const MeasurementInput(),
    bodyFat: const MeasurementInput(sourceType: 'device_estimate'),
    waist: const MeasurementInput(),
    hip: const MeasurementInput(),
    occupationalActivity: '',
    averageSteps: '',
    activeCommuting: false,
    movementNote: '',
    manualPalOverride: '',
    sports: const [],
    dietaryPreference: '',
    allergies: '',
    intolerances: '',
    excludedFoods: '',
    dislikedFoods: '',
    preferredMeals: '3',
    mealTiming: '',
    healthFlags: const {
      'pregnant': false,
      'breastfeeding': false,
      'diagnosed_eating_disorder': false,
      'diabetes': false,
      'kidney_disease': false,
      'liver_disease': false,
      'medically_prescribed_diet': false,
      'serious_metabolic_condition': false,
      'other_professional_nutrition_condition': false,
    },
    healthNote: '',
    consentAccepted: false,
    consentTextVersion: AppBranding.consentTextVersion,
  );

  factory OnboardingDraft.fromStoredProfile({
    required Map<String, dynamic> profile,
    required Map<String, dynamic> activity,
    required Map<String, dynamic> goal,
    required List<Map<String, dynamic>> restrictions,
    required Map<String, dynamic> health,
    required DateTime now,
  }) {
    final initial = OnboardingDraft.initial(now);
    final rawMeasurements = profile['measurements'];
    final measurements = rawMeasurements is List
        ? rawMeasurements.whereType<Map>().toList(growable: false)
        : const <Map>[];
    MeasurementInput measurement(String type, {String source = 'measured'}) {
      final match = measurements.where(
        (item) => item['measurement_type']?.toString() == type,
      );
      if (match.isEmpty) return MeasurementInput(sourceType: source);
      return MeasurementInput.fromJson(match.first);
    }

    String restrictionsOf(String type) => restrictions
        .where((item) => item['restriction_type']?.toString() == type)
        .map((item) => item['value']?.toString() ?? '')
        .where((value) => value.isNotEmpty)
        .join(', ');

    String text(Object? value) => value?.toString() ?? '';
    final flags = <String, bool>{
      for (final key in initial.healthFlags.keys) key: health[key] == true,
    };
    final rawSports = activity['sports'];
    final sports = rawSports is List
        ? rawSports.map(SportInput.fromJson).toList(growable: false)
        : const <SportInput>[];

    return OnboardingDraft(
      schemaVersion: initial.schemaVersion,
      currentStep: 0,
      startedAt: initial.startedAt,
      updatedAt: initial.updatedAt,
      clientRequestId: initial.clientRequestId,
      goalType: text(goal['goal_type']),
      targetWeightKg: text(goal['target_weight_kg']),
      desiredIntensity: text(goal['desired_intensity']).isEmpty
          ? 'mild'
          : text(goal['desired_intensity']),
      requestedWeeklyRateKg: text(goal['requested_weekly_rate_kg']),
      birthDate: text(profile['birth_date']),
      heightCm: text(profile['height_cm']),
      weightKg: text(profile['current_weight_kg']),
      physiologicalCategory: text(profile['physiological_category']),
      measuredRee: measurement('measured_resting_energy_expenditure'),
      bodyFat: measurement('body_fat_percentage', source: 'device_estimate'),
      waist: measurement('waist_circumference'),
      hip: measurement('hip_circumference'),
      occupationalActivity: text(activity['occupational_activity_category']),
      averageSteps: text(activity['average_daily_steps']),
      activeCommuting: activity['active_commuting'] == true,
      movementNote: text(activity['movement_notes']),
      manualPalOverride: text(activity['manual_pal_override']),
      sports: sports,
      dietaryPreference: text(profile['dietary_preference']),
      allergies: restrictionsOf('allergy'),
      intolerances: restrictionsOf('intolerance'),
      excludedFoods: restrictionsOf('excluded_food'),
      dislikedFoods: restrictionsOf('disliked_food'),
      preferredMeals: text(profile['preferred_meals_per_day']).isEmpty
          ? '3'
          : text(profile['preferred_meals_per_day']),
      mealTiming: text(profile['preferred_meal_timing']),
      healthFlags: flags,
      healthNote: text(health['user_note']),
      consentAccepted: false,
      consentTextVersion: AppBranding.consentTextVersion,
    );
  }

  final int schemaVersion;
  final int currentStep;
  final DateTime startedAt;
  final DateTime updatedAt;
  final String clientRequestId;
  final String goalType;
  final String targetWeightKg;
  final String desiredIntensity;
  final String requestedWeeklyRateKg;
  final String birthDate;
  final String heightCm;
  final String weightKg;
  final String physiologicalCategory;
  final MeasurementInput measuredRee;
  final MeasurementInput bodyFat;
  final MeasurementInput waist;
  final MeasurementInput hip;
  final String occupationalActivity;
  final String averageSteps;
  final bool activeCommuting;
  final String movementNote;
  final String manualPalOverride;
  final List<SportInput> sports;
  final String dietaryPreference;
  final String allergies;
  final String intolerances;
  final String excludedFoods;
  final String dislikedFoods;
  final String preferredMeals;
  final String mealTiming;
  final Map<String, bool> healthFlags;
  final String healthNote;
  final bool consentAccepted;
  final String consentTextVersion;

  bool isExpired(DateTime now, {Duration maxAge = const Duration(days: 30)}) =>
      now.toUtc().difference(updatedAt.toUtc()) > maxAge;

  double get totalWeeklySportMinutes =>
      sports.fold(0, (total, sport) => total + sport.weeklyMinutes);

  OnboardingDraft withField(String field, Object? value, DateTime now) {
    final json = toJson();
    json[field] = value;
    json['updated_at'] = now.toUtc().toIso8601String();
    return OnboardingDraft.fromJson(json);
  }

  Map<String, dynamic> toJson() => {
    'schema_version': schemaVersion,
    'current_step': currentStep,
    'started_at': startedAt.toUtc().toIso8601String(),
    'updated_at': updatedAt.toUtc().toIso8601String(),
    'client_request_id': clientRequestId,
    'goal_type': goalType,
    'target_weight_kg': targetWeightKg,
    'desired_intensity': desiredIntensity,
    'requested_weekly_rate_kg': requestedWeeklyRateKg,
    'birth_date': birthDate,
    'height_cm': heightCm,
    'weight_kg': weightKg,
    'physiological_category': physiologicalCategory,
    'measured_ree': measuredRee.toJson(),
    'body_fat': bodyFat.toJson(),
    'waist': waist.toJson(),
    'hip': hip.toJson(),
    'occupational_activity': occupationalActivity,
    'average_steps': averageSteps,
    'active_commuting': activeCommuting,
    'movement_note': movementNote,
    'manual_pal_override': manualPalOverride,
    'sports': sports.map((sport) => sport.toJson()).toList(),
    'dietary_preference': dietaryPreference,
    'allergies': allergies,
    'intolerances': intolerances,
    'excluded_foods': excludedFoods,
    'disliked_foods': dislikedFoods,
    'preferred_meals': preferredMeals,
    'meal_timing': mealTiming,
    'health_flags': healthFlags,
    'health_note': healthNote,
    'consent_accepted': consentAccepted,
    'consent_text_version': consentTextVersion,
  };

  factory OnboardingDraft.fromJson(Map<String, dynamic> json) {
    final now = DateTime.now().toUtc();
    final rawSports = json['sports'];
    final rawFlags = json['health_flags'];
    return OnboardingDraft(
      schemaVersion: (json['schema_version'] as num?)?.toInt() ?? 1,
      currentStep: ((json['current_step'] as num?)?.toInt() ?? 0)
          .clamp(0, 9)
          .toInt(),
      startedAt: DateTime.tryParse(json['started_at']?.toString() ?? '') ?? now,
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ?? now,
      clientRequestId: json['client_request_id']?.toString() ?? _uuidV4(),
      goalType: json['goal_type']?.toString() ?? '',
      targetWeightKg: json['target_weight_kg']?.toString() ?? '',
      desiredIntensity: json['desired_intensity']?.toString() ?? 'mild',
      requestedWeeklyRateKg: json['requested_weekly_rate_kg']?.toString() ?? '',
      birthDate: json['birth_date']?.toString() ?? '',
      heightCm: json['height_cm']?.toString() ?? '',
      weightKg: json['weight_kg']?.toString() ?? '',
      physiologicalCategory: json['physiological_category']?.toString() ?? '',
      measuredRee: MeasurementInput.fromJson(json['measured_ree']),
      bodyFat: MeasurementInput.fromJson(json['body_fat']),
      waist: MeasurementInput.fromJson(json['waist']),
      hip: MeasurementInput.fromJson(json['hip']),
      occupationalActivity: json['occupational_activity']?.toString() ?? '',
      averageSteps: json['average_steps']?.toString() ?? '',
      activeCommuting: json['active_commuting'] == true,
      movementNote: json['movement_note']?.toString() ?? '',
      manualPalOverride: json['manual_pal_override']?.toString() ?? '',
      sports: rawSports is List
          ? rawSports.map(SportInput.fromJson).toList(growable: false)
          : const [],
      dietaryPreference: json['dietary_preference']?.toString() ?? '',
      allergies: json['allergies']?.toString() ?? '',
      intolerances: json['intolerances']?.toString() ?? '',
      excludedFoods: json['excluded_foods']?.toString() ?? '',
      dislikedFoods: json['disliked_foods']?.toString() ?? '',
      preferredMeals: json['preferred_meals']?.toString() ?? '3',
      mealTiming: json['meal_timing']?.toString() ?? '',
      healthFlags: rawFlags is Map
          ? Map<String, bool>.fromEntries(
              rawFlags.entries.map(
                (entry) => MapEntry(entry.key.toString(), entry.value == true),
              ),
            )
          : OnboardingDraft.initial(now).healthFlags,
      healthNote: json['health_note']?.toString() ?? '',
      consentAccepted: json['consent_accepted'] == true,
      consentTextVersion:
          json['consent_text_version']?.toString() ??
          AppBranding.consentTextVersion,
    );
  }

  Map<String, dynamic> profileRequest() => {
    'birth_date': birthDate,
    'physiological_category': physiologicalCategory,
    'height_cm': GermanDecimal.parse(heightCm),
    'current_weight_kg': GermanDecimal.parse(weightKg),
    'dietary_preference': dietaryPreference,
    'preferred_meals_per_day': int.parse(preferredMeals),
    if (mealTiming.trim().isNotEmpty)
      'preferred_meal_timing': mealTiming.trim(),
    'measurements': measurementRequests(),
  };

  List<Map<String, dynamic>> measurementRequests() {
    final values = <(String, String, MeasurementInput)>[
      ('measured_resting_energy_expenditure', 'kcal/day', measuredRee),
      ('body_fat_percentage', '%', bodyFat),
      ('waist_circumference', 'cm', waist),
      ('hip_circumference', 'cm', hip),
    ];
    return values
        .where((entry) => !entry.$3.isEmpty)
        .map(
          (entry) => {
            'measurement_type': entry.$1,
            'value': GermanDecimal.parse(entry.$3.value),
            'unit': entry.$2,
            'measured_at': _isoDate(entry.$3.measuredAt ?? DateTime.now()),
            'source_type': entry.$3.sourceType,
          },
        )
        .toList(growable: false);
  }

  Map<String, dynamic> activityRequest() => {
    'occupational_activity_category': occupationalActivity,
    if (averageSteps.trim().isNotEmpty)
      'average_daily_steps': GermanDecimal.parse(averageSteps).round(),
    'active_commuting': activeCommuting,
    if (movementNote.trim().isNotEmpty) 'movement_notes': movementNote.trim(),
    if (manualPalOverride.trim().isNotEmpty)
      'manual_pal_override': GermanDecimal.parse(manualPalOverride),
    'sports': sports.map((sport) => sport.toApiJson()).toList(),
  };

  Map<String, dynamic> goalRequest() => {
    'goal_type': goalType,
    if (targetWeightKg.trim().isNotEmpty)
      'target_weight_kg': GermanDecimal.parse(targetWeightKg),
    if (goalType == 'lose_weight' || goalType == 'gain_weight')
      'desired_intensity': desiredIntensity,
    if ((goalType == 'lose_weight' || goalType == 'gain_weight') &&
        requestedWeeklyRateKg.trim().isNotEmpty)
      'requested_weekly_rate_kg': GermanDecimal.parse(requestedWeeklyRateKg),
  };

  List<Map<String, dynamic>> restrictionRequest() {
    List<Map<String, dynamic>> entries(String type, String raw, bool hard) =>
        raw
            .split(',')
            .map((value) => value.trim())
            .where((value) => value.isNotEmpty)
            .map(
              (value) => {
                'restriction_type': type,
                'value': value,
                'hard_exclusion': hard,
              },
            )
            .toList();
    return [
      ...entries('allergy', allergies, true),
      ...entries('intolerance', intolerances, true),
      ...entries('excluded_food', excludedFoods, true),
      ...entries('disliked_food', dislikedFoods, false),
    ];
  }

  Map<String, dynamic> healthRequest() => {
    ...healthFlags,
    if (healthNote.trim().isNotEmpty) 'user_note': healthNote.trim(),
  };

  Map<String, dynamic> consentRequest() => {
    'purpose_code': AppBranding.consentPurpose,
    'consent_text_version': consentTextVersion,
    'affirmed': true,
    'source': 'android_onboarding',
  };
}

String _isoDate(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

String _uuidV4() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes
      .map((value) => value.toRadixString(16).padLeft(2, '0'))
      .join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-'
      '${hex.substring(16, 20)}-${hex.substring(20)}';
}
