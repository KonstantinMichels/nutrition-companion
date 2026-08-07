import 'package:flutter/material.dart';

import '../../app/theme.dart';

final class ContentWidth extends StatelessWidget {
  const ContentWidth({
    required this.child,
    this.padding = const EdgeInsets.all(AppTheme.pagePadding),
    super.key,
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.topCenter,
    child: SingleChildScrollView(
      padding: padding,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: child,
      ),
    ),
  );
}
