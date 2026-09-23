import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/constants/categories.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/features/dashboard/today_controller.dart';

/// The primary OWNLY screen: "What do I need to do about the things I own today?"
class TodayScreen extends ConsumerWidget {
  const TodayScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(todayProvider);
    final d = state.dashboard;

    return RefreshIndicator(
      onRefresh: () => ref.read(todayProvider.notifier).refresh(),
      child: Scaffold(
        appBar: AppBar(
          title: Text(d == null ? 'Today' : '${d.greeting} 👋'),
        ),
        body: state.loading && d == null
            ? const Center(child: CircularProgressIndicator())
            : state.error != null && d == null
                ? _ErrorView(message: state.error!, onRetry: () => ref.read(todayProvider.notifier).refresh())
                : _DashboardView(dashboard: d!),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 48, color: OwnlyTheme.muted),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center,
                style: const TextStyle(color: OwnlyTheme.muted)),
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: const Text('Try again')),
          ],
        ),
      ),
    );
  }
}

class _DashboardView extends StatelessWidget {
  final TodayDashboard dashboard;
  const _DashboardView({required this.dashboard});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        _StatsRow(stats: dashboard.stats),
        if (dashboard.attention.isNotEmpty) ...[
          const _SectionHeader('Needs attention'),
          for (final a in dashboard.attention) _AttentionCard(item: a),
        ],
        if (dashboard.upcoming.isNotEmpty) ...[
          const _SectionHeader('Upcoming'),
          for (final u in dashboard.upcoming) _UpcomingTile(item: u),
        ],
        if (dashboard.recentlyAdded.isNotEmpty) ...[
          const _SectionHeader('Recently added'),
          for (final p in dashboard.recentlyAdded) _ProductTile(product: p),
        ],
        if (dashboard.attention.isEmpty &&
            dashboard.upcoming.isEmpty &&
            dashboard.recentlyAdded.isEmpty)
          const Padding(
            padding: EdgeInsets.all(48),
            child: Column(children: [
              Icon(Icons.inventory_2_outlined, size: 56, color: OwnlyTheme.muted),
              SizedBox(height: 12),
              Text('Nothing needs your attention.\nAdd your first product to get started.',
                textAlign: TextAlign.center,
                style: TextStyle(color: OwnlyTheme.muted)),
            ]),
          ),
      ],
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
      child: Text(title,
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(fontWeight: FontWeight.w700, color: OwnlyTheme.muted)),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final DashboardStats stats;
  const _StatsRow({required this.stats});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _Stat(value: stats.totalProducts, label: 'Products'),
              _Stat(value: stats.activeWarranties, label: 'Warranties'),
              _Stat(value: stats.expiringWarranties, label: 'Expiring', highlight: stats.expiringWarranties > 0),
              _Stat(value: stats.documentsStored, label: 'Documents'),
            ],
          ),
        ),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final int value;
  final String label;
  final bool highlight;
  const _Stat({required this.value, required this.label, this.highlight = false});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('$value',
            style: TextStyle(
              fontSize: 22, fontWeight: FontWeight.w800,
              color: highlight ? OwnlyTheme.warning : OwnlyTheme.ink,
            )),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted)),
      ],
    );
  }
}

class _AttentionCard extends StatelessWidget {
  final AttentionItem item;
  const _AttentionCard({required this.item});

  Color get _severityColor =>
      item.severity == 'critical' ? OwnlyTheme.danger : OwnlyTheme.warning;

  IconData get _icon => switch (item.kind) {
        'warranty_expiring' => Icons.verified_user_outlined,
        'return_expiring' => Icons.undo_outlined,
        'service_due' => Icons.build_circle_outlined,
        _ => Icons.notifications_active_outlined,
      };

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: _severityColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(_icon, color: _severityColor),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.title,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(item.message,
                      style: const TextStyle(color: OwnlyTheme.muted, fontSize: 13)),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: _severityColor),
          ],
        ),
      ),
    );
  }
}

class _UpcomingTile extends StatelessWidget {
  final UpcomingItem item;
  const _UpcomingTile({required this.item});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.event_outlined, color: OwnlyTheme.seed),
        title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${Formatters.shortDate(item.dueDate)} · ${Formatters.daysRemaining(item.daysRemaining)}'),
      ),
    );
  }
}

class _ProductTile extends StatelessWidget {
  final Product product;
  const _ProductTile({required this.product});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: OwnlyTheme.seed.withValues(alpha: 0.1),
          child: Icon(categoryIcon(product.category),
              color: OwnlyTheme.seed, size: 20),
        ),
        title: Text(product.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(product.brand ?? categoryLabel(product.category)),
        trailing: Chip(
          label: Text(
            statusLabel(product.warranty.status),
            style: TextStyle(
              fontSize: 11,
              color: statusColor(product.warranty.status),
              fontWeight: FontWeight.w600,
            ),
          ),
          backgroundColor: statusColor(product.warranty.status).withValues(alpha: 0.1),
          side: BorderSide.none,
        ),
      ),
    );
  }
}