import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:ownly/core/theme/ownly_theme.dart';

/// First-run flag: true once the user has completed onboarding.
/// Persisted in SharedPreferences so it survives restarts.
class OnboardingController extends AsyncNotifier<bool> {
  static const prefsKey = 'ownly_onboarding_done';

  @override
  Future<bool> build() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(prefsKey) ?? false;
  }

  /// Marks onboarding complete; the router reacts and opens /today.
  Future<void> complete() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefsKey, true);
    state = const AsyncValue.data(true);
  }
}

final onboardingDoneProvider =
    AsyncNotifierProvider<OnboardingController, bool>(OnboardingController.new);

/// First-run explainer: what OWNLY does and why it's privacy-first.
class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 40, 24, 24),
          children: [
            Icon(Icons.verified_user_outlined,
                size: 64, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              'OWNLY',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.5,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              'Your personal digital ownership assistant',
              textAlign: TextAlign.center,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: OwnlyTheme.muted),
            ),
            const SizedBox(height: 32),
            const _Highlight(
              icon: Icons.notifications_none,
              title: 'Never miss a deadline',
              body: 'Warranty expiries, return windows and service dates — '
                  'reminded while there is still time to act.',
            ),
            const _Highlight(
              icon: Icons.receipt_long_outlined,
              title: 'Every receipt in one place',
              body: 'Scan or upload receipts, invoices and manuals, then '
                  'find them exactly when you need them.',
            ),
            const _Highlight(
              icon: Icons.lock_outline,
              title: 'Privacy first',
              body: 'Your data is yours: export everything at any time, or '
                  'delete your account and every file for good.',
            ),
            const SizedBox(height: 32),
            FilledButton(
              onPressed: () =>
                  ref.read(onboardingDoneProvider.notifier).complete(),
              child: const Text('Get started'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Highlight extends StatelessWidget {
  final IconData icon;
  final String title;
  final String body;
  const _Highlight({required this.icon, required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: OwnlyTheme.seed.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: OwnlyTheme.seed, size: 22),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(body,
                    style: const TextStyle(
                        fontSize: 13, color: OwnlyTheme.muted, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}