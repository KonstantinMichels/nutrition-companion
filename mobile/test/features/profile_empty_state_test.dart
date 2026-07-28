import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/features/profile/profile_screen.dart';

void main() {
  testWidgets('missing profile shows a creation action', (tester) async {
    final router = GoRouter(
      initialLocation: '/profile',
      routes: [
        GoRoute(path: '/profile', builder: (_, _) => const ProfileScreen()),
        GoRoute(
          path: '/onboarding',
          builder: (_, _) => const Scaffold(body: Text('Onboarding')),
        ),
        GoRoute(
          path: '/home',
          builder: (_, _) => const Scaffold(body: Text('Hauptseite')),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [profileBundleProvider.overrideWith((_) async => null)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Noch kein Profil vorhanden'), findsOneWidget);
    expect(find.text('Profil anlegen'), findsOneWidget);

    await tester.tap(find.text('Profil anlegen'));
    await tester.pumpAndSettle();

    expect(router.state.uri.path, '/onboarding');
  });
}
