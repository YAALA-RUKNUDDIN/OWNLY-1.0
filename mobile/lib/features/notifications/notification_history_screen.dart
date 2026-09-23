import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:ownly/core/constants/api_constants.dart';
import 'package:ownly/core/notifications/notification_payload.dart';
import 'package:ownly/core/notifications/notification_service.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

/// Notification history — what OWNLY has already told this user.
/// Paginated GET /notifications with optional category filter (Phase 5 adds
/// FCM push + notification-tap routing through the same categories).
class NotificationHistoryScreen extends ConsumerStatefulWidget {
  const NotificationHistoryScreen({super.key});

  @override
  ConsumerState<NotificationHistoryScreen> createState() =>
      _NotificationHistoryScreenState();
}

class _NotificationHistoryScreenState
    extends ConsumerState<NotificationHistoryScreen> {
  static const Map<String?, String> _categories = {
    null: 'All',
    'warranty': 'Warranty',
    'return_window': 'Return window',
    'service': 'Service',
    'custom': 'Custom',
  };

  String? _category;
  int _page = 1;
  int _total = 0;
  bool _loading = false;
  bool _loadingMore = false;
  String? _error;
  List<NotificationItem> _items = const [];

  @override
  void initState() {
    super.initState();
    _loading = true;
    _fetch();
  }

  Future<void> _fetch() async {
    try {
      final result = await ref.read(repositoryProvider).notifications(
            category: _category,
            page: _page,
          );
      if (!mounted) return;
      setState(() {
        _items = _page == 1 ? result.items : [..._items, ...result.items];
        _total = result.total;
        _loading = false;
        _loadingMore = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
        _loadingMore = false;
      });
    }
  }

  void _applyCategory(String? category) {
    setState(() {
      _category = category;
      _page = 1;
      _items = const [];
      _loading = true;
    });
    _fetch();
  }

  void _loadMore() {
    setState(() {
      _page += 1;
      _loadingMore = true;
    });
    _fetch();
  }

  Future<void> _sendTestNotification() async {
    try {
      final notifs = ref.read(notificationServiceProvider);
      // Trigger via local notification service for instant verification
      await notifs.showNotification(
        title: 'OWNLY Test Alert',
        body: 'Tap to view your reminders and upcoming items.',
        payload: const NotificationPayload(
          route: OwnlyRoutes.reminders,
          title: 'OWNLY Test Alert',
        ),
      );
      // Also request backend test notification if available
      try {
        await ref.read(repositoryProvider).sendTestNotification(
              title: 'OWNLY Test Alert',
              body: 'Tap to view your reminders and upcoming items.',
              route: OwnlyRoutes.reminders,
            );
        _page = 1;
        _fetch();
      } catch (_) {}

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Test notification dispatched! Check your notifications.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not send test notification: $e')),
      );
    }
  }

  String _categoryLabel(String category) => _categories[category] ?? category;

  void _onItemTapped(NotificationItem item) {
    if (item.subjectType == 'reminder') {
      context.push(OwnlyRoutes.reminders);
    } else if (item.subjectType == 'warranty' || item.subjectType == 'product' || item.subjectType == 'return') {
      context.push(OwnlyRoutes.productPath(item.subjectId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasMore = _items.length < _total;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification history'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notification_add_outlined),
            tooltip: 'Send test notification',
            onPressed: _sendTestNotification,
          ),
          PopupMenuButton<String?>(
            icon: const Icon(Icons.filter_alt_outlined),
            tooltip: 'Filter by category',
            onSelected: _applyCategory,
            itemBuilder: (_) => [
              for (final entry in _categories.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
          ),
        ],
      ),
      body: _loading && _items.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _items.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Could not load notifications: $_error',
                            textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        FilledButton.tonal(
                            onPressed: () {
                              setState(() {
                                _page = 1;
                                _loading = true;
                              });
                              _fetch();
                            },
                            child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : _items.isEmpty
                  ? const Center(
                      child: Text('No notifications yet.',
                          style: TextStyle(color: OwnlyTheme.muted)),
                    )
                  : ListView(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                      children: [
                        if (_category != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Text(
                              'Filtered: ${_categoryLabel(_category!)}',
                              style: const TextStyle(
                                  color: OwnlyTheme.muted, fontSize: 13),
                            ),
                          ),
                        for (final item in _items)
                          Card(
                            clipBehavior: Clip.antiAlias,
                            child: InkWell(
                              onTap: () => _onItemTapped(item),
                              child: Padding(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(item.title,
                                              style: const TextStyle(
                                                  fontWeight: FontWeight.w700)),
                                        ),
                                        const Icon(Icons.chevron_right,
                                            size: 18, color: OwnlyTheme.muted),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(item.body,
                                        style: const TextStyle(
                                            color: OwnlyTheme.muted)),
                                    const SizedBox(height: 8),
                                    Text(
                                      '${_categoryLabel(item.category)} · '
                                      '${item.sentAt == null ? '—' : Formatters.shortDate(item.sentAt!)} · '
                                      '${item.deliveryStatus}',
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        if (hasMore)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Center(
                              child: _loadingMore
                                  ? const CircularProgressIndicator()
                                  : OutlinedButton(
                                      onPressed: _loadMore,
                                      child: Text(
                                          'Load more (${_items.length} of $_total)'),
                                    ),
                            ),
                          ),
                      ],
                    ),
    );
  }
}