import 'package:flutter/material.dart';
import 'dart:math' as math;

import '../../app/theme.dart';

final class ContentWidth extends StatelessWidget {
  const ContentWidth({
    required this.child,
    this.padding = const EdgeInsets.fromLTRB(
      AppLayout.sectionOuterMargin,
      AppSpacing.sm,
      AppLayout.sectionOuterMargin,
      AppSpacing.xl,
    ),
    this.includeNavigationInset = true,
    super.key,
  });

  final Widget child;
  final EdgeInsets padding;
  final bool includeNavigationInset;

  @override
  Widget build(BuildContext context) {
    final effectivePadding = includeNavigationInset
        ? padding.copyWith(
            bottom: math.max(
              padding.bottom,
              AppLayout.navigationContentInset +
                  MediaQuery.viewPaddingOf(context).bottom,
            ),
          )
        : padding;
    return Align(
      alignment: Alignment.topCenter,
      child: SingleChildScrollView(
        padding: effectivePadding,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: child,
        ),
      ),
    );
  }
}
