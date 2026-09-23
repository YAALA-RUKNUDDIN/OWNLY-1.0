import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/authentication/auth_controller.dart';

/// Profile: notification preferences, data export, account deletion, logout.
/// Privacy-first: users own their data and can leave with everything.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _busy = false;
  late Future<List<NotificationPref>> _prefs;

  @override
  void initState() {
    super.initState();
    _prefs = ref.read(repositoryProvider).notificationPrefs();
  }

  Future<void> _toggle(NotificationPref pref, bool enabled) async {
    try {
      final updated = await ref.read(repositoryProvider).updateNotificationPref(
            pref.category,
            enabled: enabled,
            leadDays: pref.leadDays,
          );
      if (mounted) setState(() => _prefs = Future.value(updated));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not save preference: $e')));
      }
    }
  }

  String _prefLabel(String category) => switch (category) {
        'warranty' => 'Warranty alerts',
        'return_window' => 'Return window alerts',
        'service' => 'Service reminders',
        'custom' => 'Custom reminders',
        _ => category,
      };

  Future<void> _export() async {
    setState(() => _busy = true);
    try {
      final data = await ref.read(repositoryProvider).exportData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
              'Export ready — ${data['products']?.length ?? 0} products. '
              'A downloadable copy would be saved here.'),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Export failed: $e')));
      }
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _deleteAccount() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete your account?'),
        content: const Text(
            'This permanently deletes your account, all products, and all '
            'documents. This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete everything', style: TextStyle(color: OwnlyTheme.danger)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await ref.read(repositoryProvider).deleteAccount();
      if (mounted) ref.read(authStateProvider.notifier).logout();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Deletion failed: $e')));
      }
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authStateProvider);
    final user = auth.asData?.value;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const CircleAvatar(
                  child: Icon(Icons.person, color: OwnlyTheme.seed)),
              title: Text(user?.name ?? 'OWNLY user',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(user?.email ?? ''),
            ),
          ),
          const SizedBox(height: 16),
          const _Header('Notifications'),
          Card(
            child: FutureBuilder<List<NotificationPref>>(
              future: _prefs,
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snap.hasError) {
                  return ListTile(
                    leading:
                        const Icon(Icons.cloud_off, color: OwnlyTheme.muted),
                    title: const Text('Could not load preferences'),
                    subtitle: const Text('Tap to retry'),
                    onTap: () => setState(
                        () => _prefs = ref.read(repositoryProvider).notificationPrefs()),
                  );
                }
                final prefs = snap.data ?? const <NotificationPref>[];
                if (prefs.isEmpty) {
                  return const ListTile(
                    title: Text('No notification preferences available.',
                        style: TextStyle(color: OwnlyTheme.muted)),
                  );
                }
                return Column(
                  children: [
                    for (final p in prefs)
                      SwitchListTile(
                        title: Text(_prefLabel(p.category)),
                        subtitle: Text(p.leadDays.isEmpty
                            ? 'On the day only'
                            : '${p.leadDays.join(' / ')} days before'),
                        value: p.enabled,
                        onChanged: (v) => _toggle(p, v),
                      ),
                  ],
                );
              },
            ),
          ),
          const SizedBox(height: 16),
          const _Header('Your data'),
          Card(
            child: Column(children: [
              ListTile(
                leading: const Icon(Icons.download_outlined),
                title: const Text('Export my data'),
                subtitle: const Text('Download everything as JSON'),
                onTap: _busy ? null : _export,
              ),
              ListTile(
                leading: const Icon(Icons.delete_forever, color: OwnlyTheme.danger),
                title: const Text('Delete account',
                    style: TextStyle(color: OwnlyTheme.danger)),
                subtitle: const Text('Permanently remove all data'),
                onTap: _busy ? null : _deleteAccount,
              ),
            ]),
          ),
          const SizedBox(height: 16),
          FilledButton.tonal(
            onPressed: _busy
                ? null
                : () => ref.read(authStateProvider.notifier).logout(),
            child: const Text('Log out'),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final String text;
  const _Header(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 6),
      child: Text(text,
          style: const TextStyle(
              fontWeight: FontWeight.w700, color: OwnlyTheme.muted, fontSize: 13)),
    );
  }
}