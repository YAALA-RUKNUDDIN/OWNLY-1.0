import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

/// Subscription: current plan, limits and usage, plus dev activate/cancel.
/// One GET /subscription payload drives feature gating app-wide.
class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({super.key});

  @override
  ConsumerState<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  late Future<SubscriptionInfo> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = ref.read(repositoryProvider).subscription();
  }

  void _reload() {
    setState(() => _future = ref.read(repositoryProvider).subscription());
  }

  Future<void> _activate() async {
    setState(() => _busy = true);
    try {
      await ref.read(repositoryProvider).activateSubscription(months: 12);
      _reload();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Premium activated for 12 months.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Activation failed: $e')));
      }
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _cancel() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel premium?'),
        content: const Text(
            'You keep premium until the current period ends, then move to the free plan.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Keep premium')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child:
                const Text('Cancel plan', style: TextStyle(color: OwnlyTheme.danger)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await ref.read(repositoryProvider).cancelSubscription();
      _reload();
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Subscription canceled.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Cancellation failed: $e')));
      }
    }
    if (mounted) setState(() => _busy = false);
  }

  String _statusCaption(SubscriptionInfo sub) {
    final status = sub.status.isEmpty
        ? ''
        : '${sub.status[0].toUpperCase()}${sub.status.substring(1)}';
    if (sub.canceledAt != null) {
      return '$status · canceled ${Formatters.shortDate(sub.canceledAt!)}';
    }
    return status;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Subscription')),
      body: FutureBuilder<SubscriptionInfo>(
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
                    Text('Could not load subscription: ${snap.error}',
                        textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton.tonal(
                        onPressed: _reload, child: const Text('Retry')),
                  ],
                ),
              ),
            );
          }
          final sub = snap.data!;
          final premium = sub.isPremium;
          final usageLabel = sub.maxProducts == null
              ? '${sub.usedProducts} products used · unlimited plan'
              : '${sub.usedProducts} of ${sub.maxProducts} products used';
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 26,
                        backgroundColor:
                            OwnlyTheme.seed.withValues(alpha: 0.1),
                        child: Icon(Icons.workspace_premium,
                            color:
                                premium ? OwnlyTheme.seed : OwnlyTheme.muted,
                            size: 28),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              premium ? 'Premium' : 'Free',
                              style: const TextStyle(
                                  fontSize: 20, fontWeight: FontWeight.w800),
                            ),
                            Text(
                              _statusCaption(sub),
                              style: const TextStyle(color: OwnlyTheme.muted),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const _SectionHeader('Usage'),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(usageLabel,
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                      if (sub.maxProducts != null) ...[
                        const SizedBox(height: 10),
                        LinearProgressIndicator(
                          value: sub.maxProducts == 0
                              ? 0
                              : (sub.usedProducts / sub.maxProducts!)
                                  .clamp(0.0, 1.0),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              if (sub.features.isNotEmpty) ...[
                const _SectionHeader('Included'),
                Card(
                  child: Column(
                    children: [
                      for (final f in sub.features)
                        ListTile(
                          dense: true,
                          leading: const Icon(Icons.check_circle,
                              color: OwnlyTheme.success, size: 20),
                          title: Text(f.replaceAll('_', ' ')),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (sub.startedAt != null || sub.expiresAt != null) ...[
                const _SectionHeader('Dates'),
                Card(
                  child: Column(children: [
                    if (sub.startedAt != null)
                      ListTile(
                        dense: true,
                        title: const Text('Started'),
                        trailing: Text(Formatters.date(sub.startedAt!)),
                      ),
                    if (sub.expiresAt != null)
                      ListTile(
                        dense: true,
                        title: const Text('Expires'),
                        trailing: Text(Formatters.date(sub.expiresAt!)),
                      ),
                  ]),
                ),
                const SizedBox(height: 24),
              ],
              if (premium && sub.canceledAt == null)
                OutlinedButton(
                  onPressed: _busy ? null : _cancel,
                  child: const Text('Cancel plan'),
                )
              else if (!premium)
                FilledButton(
                  onPressed: _busy ? null : _activate,
                  child: _busy
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Text('Activate premium'),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String text;
  const _SectionHeader(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 6),
      child: Text(text,
          style: const TextStyle(
              fontWeight: FontWeight.w700,
              color: OwnlyTheme.muted,
              fontSize: 13)),
    );
  }
}