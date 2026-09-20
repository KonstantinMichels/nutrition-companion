import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import 'design_system.dart';

final class AppScaffold extends StatefulWidget {
  const AppScaffold({
    required this.title,
    required this.body,
    this.actions,
    this.floatingActionButton,
    this.showNavigation = true,
    this.revealRootBackground = false,
    this.showAppBar = true,
    this.respectTopSafeArea = true,
    this.onBackPressed,
    super.key,
  });

  final String title;
  final Widget body;
  final List<Widget>? actions;
  final Widget? floatingActionButton;
  final bool showNavigation;
  final bool revealRootBackground;
  final bool showAppBar;
  final bool respectTopSafeArea;
  final VoidCallback? onBackPressed;

  @override
  State<AppScaffold> createState() => _AppScaffoldState();
}

final class _AppScaffoldState extends State<AppScaffold> {
  static const _exitConfirmationWindow = Duration(seconds: 2);
  DateTime? _lastHomeBackPress;

  @override
  Widget build(BuildContext context) {
    final overlayStyle = Theme.of(context).brightness == Brightness.light
        ? SystemUiOverlayStyle.dark
        : SystemUiOverlayStyle.light;
    return PopScope<Object?>(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _handleBack();
      },
      child: AnnotatedRegion<SystemUiOverlayStyle>(
        value: overlayStyle.copyWith(
          statusBarColor: Colors.transparent,
          systemNavigationBarColor: Colors.transparent,
          systemNavigationBarContrastEnforced: false,
        ),
        child: Scaffold(
          extendBody: true,
          backgroundColor: Colors.black,
          appBar: null,
          body: _screenBody(context),
          floatingActionButton: widget.floatingActionButton,
          bottomNavigationBar: widget.showNavigation
              ? SafeArea(
                  top: false,
                  minimum: const EdgeInsets.only(
                    bottom: AppLayout.navigationBottomMargin,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppLayout.navigationHorizontalMargin,
                    ),
                    child: ClipRRect(
                      borderRadius: const BorderRadius.all(
                        Radius.circular(AppRadii.section),
                      ),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                        child: const _PrimaryNavigation(),
                      ),
                    ),
                  ),
                )
              : null,
        ),
      ),
    );
  }

  Widget _screenBody(BuildContext context) {
    final content = Padding(
      padding: EdgeInsets.symmetric(
        horizontal: widget.revealRootBackground
            ? 0
            : AppLayout.sectionOuterMargin,
      ),
      child: Material(
        color: widget.revealRootBackground
            ? Colors.transparent
            : Theme.of(context).colorScheme.surface,
        clipBehavior: widget.revealRootBackground ? Clip.none : Clip.antiAlias,
        borderRadius: widget.revealRootBackground
            ? null
            : BorderRadius.circular(AppRadii.section),
        child: SafeArea(
          top: !widget.showAppBar && widget.respectTopSafeArea,
          bottom: false,
          child: widget.body,
        ),
      ),
    );

    if (!widget.showAppBar) return content;
    return Column(
      children: [
        NutritionHeroSection(
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              ...?widget.actions,
            ],
          ),
        ),
        const SizedBox(height: AppLayout.sectionGap),
        Expanded(child: content),
      ],
    );
  }

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

  static const _destinations = [
    (Icons.home_outlined, Icons.home, 'Start', '/home'),
    (Icons.event_note_outlined, Icons.event_note, 'Plan', '/daily-plan'),
    (
      Icons.restaurant_menu_outlined,
      Icons.restaurant_menu,
      'Verzehr',
      '/consumption',
    ),
    (Icons.inventory_2_outlined, Icons.inventory_2, 'Vorrat', '/pantry'),
    (Icons.grid_view_outlined, Icons.grid_view, 'Mehr', '/more'),
  ];

  @override
  Widget build(BuildContext context) {
    final router = GoRouter.maybeOf(context);
    final path = router?.state.uri.path ?? '/home';
    final selectedIndex = _selectedIndex(path);
    final theme = Theme.of(context);
    final navigationTheme = theme.navigationBarTheme;
    return Material(
      key: const Key('primary-navigation'),
      color:
          navigationTheme.backgroundColor ??
          theme.colorScheme.surfaceContainerHigh.withValues(alpha: 0.9),
      child: SizedBox(
        height: AppLayout.navigationHeight,
        child: Row(
          children: [
            for (var index = 0; index < _destinations.length; index++)
              Expanded(
                child: _NavigationItem(
                  index: index,
                  icon: _destinations[index].$1,
                  selectedIcon: _destinations[index].$2,
                  label: _destinations[index].$3,
                  selected: index == selectedIndex,
                  onTap: router == null
                      ? null
                      : () => router.go(_destinations[index].$4),
                ),
              ),
          ],
        ),
      ),
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

final class _NavigationItem extends StatelessWidget {
  const _NavigationItem({
    required this.index,
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final int index;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final foreground = selected ? scheme.primary : scheme.onSurfaceVariant;
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadii.large),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.xxs,
            vertical: AppSpacing.xs,
          ),
          child: AnimatedContainer(
            key: Key('primary-navigation-destination-$index'),
            duration: const Duration(milliseconds: 180),
            decoration: BoxDecoration(
              color: selected ? scheme.primaryContainer : Colors.transparent,
              borderRadius: BorderRadius.circular(AppRadii.large),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(selected ? selectedIcon : icon, color: foreground),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: foreground,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
