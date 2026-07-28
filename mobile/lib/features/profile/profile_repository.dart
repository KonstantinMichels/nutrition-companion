import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/api/api_client.dart';
import '../../core/errors/app_exception.dart';

final profileRepositoryProvider = Provider<ProfileRepository>(
  (ref) => ProfileRepository(ref.watch(apiClientProvider)),
);

final class ProfileBundle {
  const ProfileBundle({
    required this.profile,
    required this.activity,
    required this.goal,
    required this.restrictions,
    required this.health,
  });

  final Map<String, dynamic> profile;
  final Map<String, dynamic> activity;
  final Map<String, dynamic> goal;
  final List<Map<String, dynamic>> restrictions;
  final Map<String, dynamic> health;
}

class ProfileRepository {
  ProfileRepository(this._api);
  final ApiClient _api;

  Future<ProfileBundle?> load() async {
    dynamic rawProfile;
    try {
      rawProfile = await _api.get('/api/v1/profile');
    } on ApiException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
    final responses = await Future.wait<dynamic>([
      _api.get('/api/v1/profile/activity'),
      _api.get('/api/v1/profile/goal'),
      _api.get('/api/v1/profile/restrictions'),
      _api.get('/api/v1/profile/health-screening'),
    ]);
    Map<String, dynamic> mapAt(int index) => responses[index] is Map
        ? Map<String, dynamic>.from(responses[index] as Map)
        : {};
    final profile = rawProfile is Map
        ? Map<String, dynamic>.from(rawProfile)
        : <String, dynamic>{};
    final restrictionEnvelope = mapAt(2);
    final rawRestrictions = restrictionEnvelope['restrictions'];
    return ProfileBundle(
      profile: profile,
      activity: mapAt(0),
      goal: mapAt(1),
      restrictions: rawRestrictions is List
          ? rawRestrictions
                .whereType<Map>()
                .map((item) => Map<String, dynamic>.from(item))
                .toList(growable: false)
          : const [],
      health: mapAt(3),
    );
  }

  Future<void> save(ProfileBundle bundle) async {
    final profile = bundle.profile;
    final rawMeasurements = profile['measurements'];
    final measurements = rawMeasurements is List
        ? rawMeasurements.whereType<Map>().map((item) {
            final value = Map<String, dynamic>.from(item);
            return {
              for (final key in const [
                'measurement_type',
                'value',
                'unit',
                'measured_at',
                'source_type',
              ])
                if (value.containsKey(key)) key: value[key],
            };
          }).toList()
        : const [];
    await _api.put(
      '/api/v1/profile',
      data: {
        for (final key in const [
          'birth_date',
          'physiological_category',
          'height_cm',
          'current_weight_kg',
          'dietary_preference',
          'preferred_meals_per_day',
          'preferred_meal_timing',
        ])
          if (profile.containsKey(key)) key: profile[key],
        'measurements': measurements,
      },
    );
    final activity = bundle.activity;
    final rawSports = activity['sports'];
    final sports = rawSports is List
        ? rawSports.whereType<Map>().map((item) {
            final value = Map<String, dynamic>.from(item);
            return {
              for (final key in const [
                'sport_type',
                'sessions_per_week',
                'minutes_per_session',
                'intensity',
                'note',
              ])
                if (value.containsKey(key)) key: value[key],
            };
          }).toList()
        : const [];
    await _api.put(
      '/api/v1/profile/activity',
      data: {
        for (final key in const [
          'occupational_activity_category',
          'average_daily_steps',
          'active_commuting',
          'movement_notes',
          'manual_pal_override',
        ])
          if (activity.containsKey(key)) key: activity[key],
        'sports': sports,
      },
    );
    final goal = bundle.goal;
    await _api.put(
      '/api/v1/profile/goal',
      data: {
        for (final key in const [
          'goal_type',
          'target_weight_kg',
          'desired_intensity',
          'requested_weekly_rate_kg',
        ])
          if (goal.containsKey(key) && goal[key] != null) key: goal[key],
      },
    );
    await _api.put(
      '/api/v1/profile/restrictions',
      data: {
        'restrictions': bundle.restrictions
            .map(
              (item) => {
                for (final key in const [
                  'restriction_type',
                  'value',
                  'hard_exclusion',
                  'note',
                ])
                  if (item.containsKey(key) && item[key] != null)
                    key: item[key],
              },
            )
            .toList(),
      },
    );
    await _api.put(
      '/api/v1/profile/health-screening',
      data: {
        for (final key in const [
          'pregnant',
          'breastfeeding',
          'diagnosed_eating_disorder',
          'diabetes',
          'kidney_disease',
          'liver_disease',
          'medically_prescribed_diet',
          'serious_metabolic_condition',
          'other_professional_nutrition_condition',
          'user_note',
        ])
          if (bundle.health.containsKey(key)) key: bundle.health[key],
      },
    );
  }
}
