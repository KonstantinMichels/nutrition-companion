import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/branding.dart';
import '../../app/providers.dart';
import '../../core/widgets/states.dart';

final bootstrapProvider = FutureProvider<String>((ref) async {
  try {
    await ref.read(apiClientProvider).health();
  } catch (_) {
    // Home and submission controllers provide the actionable retry/cached state.
    // Initialization must still allow an offline draft to be opened.
  }
  final draft = await ref.read(draftRepositoryProvider).restore();
  if (draft != null) return '/onboarding';
  return '/home';
});

final class BootstrapScreen extends ConsumerStatefulWidget {
  const BootstrapScreen({super.key});

  @override
  ConsumerState<BootstrapScreen> createState() => _BootstrapScreenState();
}

final class _BootstrapScreenState extends ConsumerState<BootstrapScreen> {
  @override
  void initState() {
    super.initState();
    _continue();
  }

  Future<void> _continue() async {
    final route = await ref.read(bootstrapProvider.future);
    if (mounted) context.go(route);
  }

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: SafeArea(
      child: Column(
        children: [
          Expanded(child: LoadingState(message: 'App wird vorbereitet …')),
          Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              AppBranding.productName,
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    ),
  );
}
