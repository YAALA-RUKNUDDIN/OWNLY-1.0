import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

/// Central reminders screen (also serves the "Timeline" tab as the
/// aggregated upcoming-events view — every deadline in one place).
class RemindersScreen extends ConsumerStatefulWidget {
  const RemindersScreen({super.key});

  @override
  ConsumerState<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends ConsumerState<RemindersScreen> {
  late Future<List<ReminderItem>> _reminders;

  @override
  void initState() {
    super.initState();
    _reminders = ref.read(repositoryProvider).reminders(status: 'upcoming');
  }

  Future<void> _reload() async {
    setState(() {
      _reminders = ref.read(repositoryProvider).reminders(status: 'upcoming');
    });
  }

  Future<void> _complete(ReminderItem r) async {
    await ref.read(repositoryProvider).updateReminder(r.id, {'status': 'completed'});
    await _reload();
  }

  Future<void> _dismiss(ReminderItem r) async {
    await ref.read(repositoryProvider).updateReminder(r.id, {'status': 'dismissed'});
    await _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reminders')),
      body: FutureBuilder<List<ReminderItem>>(
        future: _reminders,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Text('Could not load reminders:\n${snap.error}',
                textAlign: TextAlign.center, style: const TextStyle(color: OwnlyTheme.muted)));
          }
          final items = snap.data ?? [];
          if (items.isEmpty) {
            return const Center(
                child: Text('No upcoming reminders.',
                    style: TextStyle(color: OwnlyTheme.muted)));
          }
          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                for (final r in items)
                  Card(
                    child: ListTile(
                      leading: Icon(
                        r.reminderType == 'service_due'
                            ? Icons.build_circle_outlined
                            : Icons.notifications_outlined,
                        color: OwnlyTheme.seed,
                      ),
                      title: Text(r.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text(
                          '${Formatters.date(r.scheduledDate)} · '
                          'due ${Formatters.daysRemaining(r.scheduledDate.difference(DateTime.now()).inDays)}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.check_circle_outline,
                                color: OwnlyTheme.success),
                            tooltip: 'Mark complete',
                            onPressed: () => _complete(r),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close, color: OwnlyTheme.muted),
                            tooltip: 'Dismiss',
                            onPressed: () => _dismiss(r),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}