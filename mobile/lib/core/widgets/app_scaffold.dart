import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

final class AppScaffold extends StatefulWidget {
  const AppScaffold({
    required this.title,
    required this.body,
    this.actions,
    this.floatingActionButton,
    this.showNavigation = true,
    this.onBackPressed,
    super.key,
  });

  final String title;
  final Widget body;
  final List<Widget>? actions;
  final Widget? floatingActionButton;
  final bool showNavigation;
  final VoidCallback? onBackPressed;

  @override
  State<AppScaffold> createState() => _AppScaffoldState();
}

final class _AppScaffoldState extends State<AppScaffold> {
  static const _exitConfirmationWindow = Duration(seconds: 2);
  DateTime? _lastHomeBackPress;

  @override
  Widget build(BuildContext context) => PopScope<Object?>(
    canPop: false,
    onPopInvokedWithResult: (didPop, _) {
      if (!didPop) _handleBack();
    },
    child: Scaffold(
      appBar: AppBar(title: Text(widget.title), actions: widget.actions),
      body: SafeArea(child: widget.body),
      floatingActionButton: widget.floatingActionButton,
      bottomNavigationBar: widget.showNavigation
          ? const _PrimaryNavigation()
          : null,
    ),
  );

  void _handleBack() {
    final customBackHandler = widget.onBackPressed;
    if (customBackHandler != null) {
      customBackHandler();
      return;
    }

    final path = GoRouterState.of(context).uri.path;
    if (path != '/home') {
      context.go('/home');
      return;
    }

    final now = DateTime.now();
    final previousPress = _lastHomeBackPress;
    if (previousPress != null &&
        now.difference(previousPress) <= _exitConfirmationWindow) {
      SystemNavigator.pop();
      return;
    }

    _lastHomeBackPress = now;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        const SnackBar(
          content: Text('Zum Beenden erneut Zurück drücken'),
          duration: _exitConfirmationWindow,
        ),
      );
  }
}

final class _PrimaryNavigation extends StatelessWidget {
  const _PrimaryNavigation();

  static const _paths = [
    '/home',
    '/daily-plan',
    '/consumption',
    '/pantry',
    '/more',
  ];

  @override
  Widget build(BuildContext context) {
    final path = GoRouterState.of(context).uri.path;
    return NavigationBar(
      selectedIndex: _selectedIndex(path),
      onDestinationSelected: (index) => context.go(_paths[index]),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Start',
        ),
        NavigationDestination(
          icon: Icon(Icons.event_note_outlined),
          selectedIcon: Icon(Icons.event_note),
          label: 'Plan',
        ),
        NavigationDestination(
          icon: Icon(Icons.restaurant_menu_outlined),
          selectedIcon: Icon(Icons.restaurant_menu),
          label: 'Verzehr',
        ),
        NavigationDestination(
          icon: Icon(Icons.inventory_2_outlined),
          selectedIcon: Icon(Icons.inventory_2),
          label: 'Vorrat',
        ),
        NavigationDestination(
          icon: Icon(Icons.grid_view_outlined),
          selectedIcon: Icon(Icons.grid_view),
          label: 'Mehr',
        ),
      ],
    );
  }

  int _selectedIndex(String path) {
    if (path.startsWith('/daily-plan')) return 1;
    if (path.startsWith('/consumption')) return 2;
    if (path.startsWith('/pantry')) return 3;
    if (path == '/home') return 0;
    return 4;
  }
}
