import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/ownly_router.dart';
import 'core/theme/ownly_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: OwnlyApp()));
}

class OwnlyApp extends ConsumerWidget {
  const OwnlyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Single navigation source of truth: onboarding + auth gates and
    // ownly:// deep links are handled inside the router (see ownly_router.dart).
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'OWNLY',
      debugShowCheckedModeBanner: false,
      theme: OwnlyTheme.light(),
      routerConfig: router,
    );
  }
}