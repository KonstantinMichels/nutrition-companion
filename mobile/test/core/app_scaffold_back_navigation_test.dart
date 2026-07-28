import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';

void main() {
  testWidgets('back on a subpage returns to home', (tester) async {
    final router = _router('/settings');
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(router.state.uri.path, '/home');
    expect(find.text('Hauptseite'), findsOneWidget);
  });

  testWidgets('back on home requires a second press to exit', (tester) async {
    final platformCalls = <MethodCall>[];
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        platformCalls.add(call);
        return null;
      },
    );
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      ),
    );
    final router = _router('/home');
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pump();

    expect(find.text('Zum Beenden erneut Zurück drücken'), findsOneWidget);
    expect(
      platformCalls.where((call) => call.method == 'SystemNavigator.pop'),
      isEmpty,
    );

    await tester.binding.handlePopRoute();
    await tester.pump();

    expect(
      platformCalls.where((call) => call.method == 'SystemNavigator.pop'),
      hasLength(1),
    );
  });

  testWidgets('a custom back handler takes precedence', (tester) async {
    var customBackCalls = 0;
    final router = GoRouter(
      initialLocation: '/custom',
      routes: [
        GoRoute(
          path: '/custom',
          builder: (_, _) => AppScaffold(
            title: 'Benutzerdefiniert',
            body: const SizedBox.shrink(),
            onBackPressed: () => customBackCalls += 1,
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pump();

    expect(customBackCalls, 1);
    expect(router.state.uri.path, '/custom');
  });
}

GoRouter _router(String initialLocation) => GoRouter(
  initialLocation: initialLocation,
  routes: [
    GoRoute(
      path: '/home',
      builder: (_, _) =>
          const AppScaffold(title: 'Hauptseite', body: SizedBox.shrink()),
    ),
    GoRoute(
      path: '/settings',
      builder: (_, _) =>
          const AppScaffold(title: 'Einstellungen', body: SizedBox.shrink()),
    ),
  ],
);
