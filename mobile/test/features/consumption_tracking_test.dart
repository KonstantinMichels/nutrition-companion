import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/app/providers.dart';
import 'package:nutrition_companion/core/api/api_client.dart';
import 'package:nutrition_companion/core/config/app_config.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/features/consumption/consumption_screen.dart';

void main() {
  testWidgets('navigation exposes explicit consumption tracking', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AppScaffold(title: 'Test', body: SizedBox.shrink()),
      ),
    );
    await tester.tap(find.byTooltip('Open navigation menu'));
    await tester.pumpAndSettle();
    expect(find.text('Verzehr'), findsOneWidget);
    expect(find.textContaining('Automatisch gegessen'), findsNothing);
  });

  test('completion and outcome wording is neutral and explicit', () {
    expect(
      consumptionAttestationLabel('complete_to_best_knowledge'),
      'Nach bestem Wissen vollständig erfasst',
    );
    expect(consumptionAttestationLabel('partial'), 'Nur teilweise erfasst');
    expect(consumptionOutcomeLabel('skipped'), 'Übersprungen');
    expect(consumptionOutcomeLabel('replaced'), 'Ersetzt');
  });

  test('consumption operation identifiers are distinct UUID v4 values', () {
    final first = consumptionOperationId();
    final second = consumptionOperationId();
    expect(
      first,
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
    expect(second, isNot(first));
  });

  testWidgets('no-day state stays explicit and creates no day automatically', (
    tester,
  ) async {
    final adapter = _ConsumptionAdapter();
    await tester.pumpWidget(_app(adapter));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('consumption-no-day')), findsOneWidget);
    expect(find.text('Leeren Tag anlegen'), findsOneWidget);
    expect(find.textContaining('automatisch als konsumiert'), findsNothing);
    expect(adapter.created, isFalse);
  });

  testWidgets('empty-day action loads explicit open consumption view', (
    tester,
  ) async {
    final adapter = _ConsumptionAdapter();
    await tester.pumpWidget(_app(adapter));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('create-empty-consumption-day')));
    await tester.pumpAndSettle();
    expect(adapter.created, isTrue);
    expect(find.text('Aufzeichnung offen'), findsOneWidget);
    expect(find.text('Vorrat bleibt unverändert'), findsOneWidget);
    expect(find.byKey(const Key('finalize-consumption-day')), findsOneWidget);
  });
}

Widget _app(_ConsumptionAdapter adapter) {
  final dio = Dio()..httpClientAdapter = adapter;
  final api = ApiClient(
    AppConfig(
      environment: AppEnvironment.development,
      apiBaseUrl: Uri.parse('http://127.0.0.1:8000'),
      allowInsecureLocalHttp: true,
    ),
    dio: dio,
  );
  return ProviderScope(
    overrides: [apiClientProvider.overrideWithValue(api)],
    child: const MaterialApp(home: ConsumptionScreen()),
  );
}

final class _ConsumptionAdapter implements HttpClientAdapter {
  bool created = false;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final path = options.uri.path;
    if (path.startsWith('/api/v1/consumption-days/by-date/')) {
      return created ? _json(200, _day()) : _error('CONSUMPTION_DAY_NOT_FOUND');
    }
    if (path.startsWith('/api/v1/daily-meal-plans/by-date/')) {
      return _error('DAILY_PLAN_NOT_FOUND');
    }
    if (path == '/api/v1/consumption/weekly-summary') {
      return _json(200, {
        'recorded_day_count': created ? 1 : 0,
        'finalized_day_count': 0,
        'complete_attestation_day_count': 0,
        'missing_day_count': created ? 6 : 7,
        'average_energy_per_recorded_day_kcal': null,
        'days': const [],
      });
    }
    if (path == '/api/v1/consumption-days' && options.method == 'POST') {
      created = true;
      return _json(201, _day());
    }
    return _error('NOT_FOUND');
  }

  Map<String, dynamic> _day() => {
    'id': '11111111-1111-4111-8111-111111111111',
    'consumption_date': DateTime.now().toIso8601String().substring(0, 10),
    'source_daily_plan_id': null,
    'assessment_id': null,
    'training_day_adjustment_id': null,
    'target_basis_source': 'none',
    'target_basis_snapshot': <String, dynamic>{},
    'status': 'open',
    'completeness_attestation': 'not_declared',
    'finalized_at': null,
    'version': 1,
    'planned_entries': const [],
    'meals': const [],
    'planned_vs_actual': {
      'planned_totals': const [],
      'actual_totals': const [],
      'differences': const [],
      'relation': 'no_plan',
    },
    'summary': {
      'actual_totals': const [],
      'target_comparison': const [],
      'quality': {
        'pending_plan_entry_count': 0,
        'unresolved_entry_count': 0,
        'basic_nutrition_complete': false,
        'warnings': const [],
      },
    },
  };

  ResponseBody _json(int status, Object body) => ResponseBody.fromString(
    jsonEncode(body),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );

  ResponseBody _error(String code) => _json(404, {
    'error': {
      'code': code,
      'message': 'Nicht gefunden',
      'field_errors': const [],
    },
  });

  @override
  void close({bool force = false}) {}
}
