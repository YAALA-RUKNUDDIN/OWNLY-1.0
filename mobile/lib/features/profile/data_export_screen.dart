import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/repositories.dart';

/// Data export — GET /users/me/export returns the user's full data as JSON.
/// Privacy-first: users can inspect everything OWNLY stores about them.
class DataExportScreen extends ConsumerStatefulWidget {
  const DataExportScreen({super.key});

  @override
  ConsumerState<DataExportScreen> createState() => _DataExportScreenState();
}

class _DataExportScreenState extends ConsumerState<DataExportScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(repositoryProvider).exportData();
  }

  void _reload() {
    setState(() => _future = ref.read(repositoryProvider).exportData());
  }

  IconData _iconFor(String key) => switch (key) {
        'products' => Icons.inventory_2_outlined,
        'documents' => Icons.description_outlined,
        'reminders' => Icons.notifications_active_outlined,
        'warranties' => Icons.verified_outlined,
        'service_records' => Icons.build_outlined,
        'repairs' => Icons.handyman_outlined,
        'notifications' => Icons.mark_email_read_outlined,
        'user' || 'account' => Icons.person_outline,
        _ => Icons.data_object,
      };

  String _describe(dynamic value) {
    if (value is List) {
      return '${value.length} item${value.length == 1 ? '' : 's'}';
    }
    if (value is Map) {
      return '${value.length} field${value.length == 1 ? '' : 's'}';
    }
    if (value == null) return '—';
    return value.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Export my data'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Regenerate export',
            onPressed: _reload,
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Export failed: ${snap.error}',
                        textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton.tonal(
                        onPressed: _reload, child: const Text('Retry')),
                  ],
                ),
              ),
            );
          }
          final data = snap.data ?? const <String, dynamic>{};
          final entries = data.entries.toList();
          if (entries.isEmpty) {
            return const Center(
              child: Text('Your export is empty.',
                  style: TextStyle(color: OwnlyTheme.muted)),
            );
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Everything OWNLY stores about you, as JSON. '
                'Each section below lists what would be in your download.',
                style: TextStyle(color: OwnlyTheme.muted, fontSize: 13),
              ),
              const SizedBox(height: 12),
              for (final entry in entries)
                Card(
                  child: ListTile(
                    leading: Icon(_iconFor(entry.key), color: OwnlyTheme.seed),
                    title: Text(entry.key.replaceAll('_', ' ')),
                    subtitle: Text(_describe(entry.value)),
                    trailing: const Icon(Icons.chevron_right,
                        color: OwnlyTheme.muted),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}