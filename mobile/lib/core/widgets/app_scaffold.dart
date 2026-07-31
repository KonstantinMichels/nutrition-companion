import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../app/branding.dart';

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
      drawer: widget.showNavigation ? const _NavigationDrawer() : null,
      body: SafeArea(child: widget.body),
      floatingActionButton: widget.floatingActionButton,
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

final class _NavigationDrawer extends StatelessWidget {
  const _NavigationDrawer();

  @override
  Widget build(BuildContext context) => NavigationDrawer(
    children: [
      const Padding(
        padding: EdgeInsets.fromLTRB(28, 24, 16, 12),
        child: Text(AppBranding.productName, style: TextStyle(fontSize: 20)),
      ),
      _destination(context, Icons.home_outlined, 'Start', '/home'),
      _destination(context, Icons.history, 'Verlauf', '/history'),
      _destination(context, Icons.show_chart, 'Fortschritt', '/progress'),
      _destination(
        context,
        Icons.restaurant_outlined,
        'Lebensmittel',
        '/foods',
      ),
      _destination(context, Icons.menu_book_outlined, 'Rezepte', '/recipes'),
      _destination(
        context,
        Icons.event_note_outlined,
        'Tagesplan',
        '/daily-plan',
      ),
      _destination(
        context,
        Icons.restaurant_menu_outlined,
        'Verzehr',
        '/consumption',
      ),
      _destination(
        context,
        Icons.calendar_view_week_outlined,
        'Wochenplan',
        '/weekly-plan',
      ),
      _destination(context, Icons.inventory_2_outlined, 'Vorrat', '/pantry'),
      _destination(
        context,
        Icons.shopping_cart_outlined,
        'Einkauf',
        '/shopping-lists',
      ),
      _destination(
        context,
        Icons.person_outline,
        'Profil bearbeiten',
        '/profile',
      ),
      _destination(
        context,
        Icons.privacy_tip_outlined,
        'Datenschutz & Daten',
        '/privacy',
      ),
      _destination(
        context,
        Icons.settings_outlined,
        'Einstellungen',
        '/settings',
      ),
    ],
  );

  Widget _destination(
    BuildContext context,
    IconData icon,
    String label,
    String path,
  ) => ListTile(
    leading: Icon(icon),
    title: Text(label),
    onTap: () {
      Navigator.of(context).pop();
      context.go(path);
    },
  );
}
