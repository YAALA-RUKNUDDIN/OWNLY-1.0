import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/claims/file_claim_dialog.dart';

/// Tab inside ProductDetailScreen showing product warranty claims and brand support.
class ClaimsTab extends ConsumerStatefulWidget {
  final Product product;

  const ClaimsTab({super.key, required this.product});

  @override
  ConsumerState<ClaimsTab> createState() => _ClaimsTabState();
}

class _ClaimsTabState extends ConsumerState<ClaimsTab> {
  bool _loading = true;
  String? _error;
  List<WarrantyClaimItem> _claims = [];
  BrandSupportItem? _brandSupport;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(claimRepositoryProvider);
      final claims = await repo.listProductClaims(widget.product.id);
      BrandSupportItem? brand;
      if (widget.product.brand != null && widget.product.brand!.isNotEmpty) {
        try {
          brand = await repo.getBrandSupport(widget.product.brand!);
        } catch (_) {
          // brand might not be in directory, ignore
        }
      }
      if (mounted) {
        setState(() {
          _claims = claims;
          _brandSupport = brand;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _fileClaim() async {
    final created = await FileClaimDialog.show(
      context,
      product: widget.product,
      warrantyId: null,
    );
    if (created != null) {
      _load();
    }
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'repaired':
      case 'replaced':
        return OwnlyTheme.success;
      case 'in_review':
      case 'submitted':
        return OwnlyTheme.warning;
      case 'rejected':
        return OwnlyTheme.danger;
      default:
        return OwnlyTheme.muted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('MMM d, yyyy');

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, style: const TextStyle(color: OwnlyTheme.danger)),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _load, child: const Text('Retry')),
          ],
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Action card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFE7EAF1)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: OwnlyTheme.seed.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.shield_outlined, color: OwnlyTheme.seed),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Warranty Claim Assistant',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                    ),
                    Text(
                      'Generate claim dossier & track RMA status',
                      style: TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                onPressed: _fileClaim,
                icon: const Icon(Icons.add, size: 16),
                label: const Text('File Claim'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: OwnlyTheme.seed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  elevation: 0,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Brand Support Directory card if matched
        if (_brandSupport != null) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE7EAF1)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.headset_mic_outlined, size: 18, color: OwnlyTheme.seed),
                    const SizedBox(width: 8),
                    Text(
                      'Official ${_brandSupport!.brand} Support',
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Hotline: ${_brandSupport!.supportPhone} (${_brandSupport!.supportHours})',
                  style: const TextStyle(fontSize: 13, color: OwnlyTheme.ink),
                ),
                const SizedBox(height: 4),
                Text(
                  'Claim portal: ${_brandSupport!.claimPortalUrl}',
                  style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],

        // Claims list
        const Text(
          'Filed Claims',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
        ),
        const SizedBox(height: 10),

        if (_claims.isEmpty)
          Container(
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE7EAF1)),
            ),
            child: const Column(
              children: [
                Icon(Icons.assignment_outlined, size: 36, color: OwnlyTheme.muted),
                SizedBox(height: 10),
                Text(
                  'No claims filed for this product yet',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: OwnlyTheme.ink),
                ),
                SizedBox(height: 4),
                Text(
                  'If hardware develops a defect or stops working, tap "File Claim" above.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                ),
              ],
            ),
          )
        else
          ..._claims.map((claim) {
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                onTap: () async {
                  await context.push('/claims/${claim.id}');
                  _load();
                },
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                title: Text(
                  claim.title,
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 4),
                    Text(
                      'Incident: ${df.format(claim.incidentDate)}${claim.claimReference != null ? ' • Ref: ${claim.claimReference}' : ''}',
                      style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                    ),
                  ],
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: _statusColor(claim.status).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        claim.status.toUpperCase(),
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: _statusColor(claim.status),
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Icon(Icons.chevron_right, size: 18, color: OwnlyTheme.muted),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }
}
