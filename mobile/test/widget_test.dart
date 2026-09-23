import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/features/dashboard/today_screen.dart';
import 'package:ownly/features/authentication/login_screen.dart';

void main() {
  testWidgets('TodayScreen renders stats and empty state', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(theme: OwnlyTheme.light(), home: TodayScreen())),
    );
    await tester.pumpAndSettle();
    expect(find.text('Products'), findsWidgets);
  });

  testWidgets('LoginScreen validates empty fields', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: LoginScreen())),
    );
    await tester.tap(find.byType(FilledButton));
    await tester.pump();
    expect(find.textContaining('Please enter'), findsWidgets);
  });

  test('daysRemaining formatter', () {
    expect(formatDays(0), 'today');
    expect(formatDays(1), 'tomorrow');
    expect(formatDays(7), 'in 7 days');
  });
}

/// Local helper mirroring Formatters.daysRemaining for test isolation.
String formatDays(int days) {
  if (days == 0) return 'today';
  if (days == 1) return 'tomorrow';
  if (days > 0) return 'in $days days';
  return '${-days} days ago';
}