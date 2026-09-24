import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/claims/claim_dossier_modal.dart';

/// Screen displaying details, status lifecycle, brand support, and dossier export for a claim.
class ClaimDetailScreen extends ConsumerStatefulWidget {
  final String claimId;

  const ClaimDetailScreen({super.key, required this.claimId});

  @override
  ConsumerState<ClaimDetailScreen> createState() => _ClaimDetailScreenState();
}

class _ClaimDetailScreenState extends ConsumerState<ClaimDetailScreen> {
  bool _loading = true;
  String? _error;
  WarrantyClaimItem? _claim;
  bool _actionLoading = false;

  @override
  void initState() {
    super.initState();
    _loadClaim();
  }

  Future<void> _loadClaim() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(claimRepositoryProvider);
      final item = await repo.getClaim(widget.claimId);
      if (mounted) {
        setState(() {
          _claim = item;
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

  Future<void> _openDossier() async {
    setState(() => _actionLoading = true);
    try {
      final repo = ref.read(claimRepositoryProvider);
      final dossier = await repo.getClaimDossier(widget.claimId);
      if (mounted) {
        setState(() => _actionLoading = false);
        ClaimDossierModal.show(context, dossier);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _actionLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load dossier: $e'), backgroundColor: OwnlyTheme.danger),
        );
      }
    }
  }

  Future<void> _updateStatusDialog() async {
    if (_claim == null) return;
    String selectedStatus = _claim!.status;
    final rmaCtrl = TextEditingController(text: _claim!.claimReference ?? '');
    final notesCtrl = TextEditingController(text: _claim!.resolutionNotes ?? '');
    final costCtrl = TextEditingController(
      text: _claim!.claimCostCovered != null ? _claim!.claimCostCovered!.toStringAsFixed(2) : '',
    );

    final statuses = [
      'draft', 'submitted', 'in_review', 'approved', 'repaired', 'replaced', 'rejected', 'closed'
    ];

    final updated = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Update Claim Status', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: selectedStatus,
                  decoration: const InputDecoration(labelText: 'Status'),
                  items: statuses
                      .map((s) => DropdownMenuItem(value: s, child: Text(s.toUpperCase())))
                      .toList(),
                  onChanged: (v) {
                    if (v != null) setDialogState(() => selectedStatus = v);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: rmaCtrl,
                  decoration: const InputDecoration(labelText: 'RMA / Case Reference #'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: costCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Cost Covered (USD)'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: notesCtrl,
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: 'Resolution / Support Notes'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: ElevatedButton.styleFrom(backgroundColor: OwnlyTheme.seed, foregroundColor: Colors.white),
              child: const Text('Save Changes'),
            ),
          ],
        ),
      ),
    );

    if (updated == true) {
      setState(() => _loading = true);
      try {
        final repo = ref.read(claimRepositoryProvider);
        final cost = double.tryParse(costCtrl.text.trim());
        final updatedClaim = await repo.updateClaim(
          widget.claimId,
          status: selectedStatus,
          claimReference: rmaCtrl.text.trim().isEmpty ? null : rmaCtrl.text.trim(),
          resolutionNotes: notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim(),
          claimCostCovered: cost,
        );
        if (mounted) {
          setState(() {
            _claim = updatedClaim;
            _loading = false;
          });
        }
      } catch (e) {
        if (mounted) {
          setState(() => _loading = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Update failed: $e'), backgroundColor: OwnlyTheme.danger),
          );
        }
      }
    }
  }

  Future<void> _deleteClaim() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Withdraw Claim?'),
        content: const Text('Are you sure you want to withdraw and remove this claim?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: TextButton.styleFrom(foregroundColor: OwnlyTheme.danger),
            child: const Text('Withdraw'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      try {
        final repo = ref.read(claimRepositoryProvider);
        await repo.deleteClaim(widget.claimId);
        if (mounted) Navigator.of(context).pop();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Delete failed: $e'), backgroundColor: OwnlyTheme.danger),
          );
        }
      }
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
      return Scaffold(
        appBar: AppBar(title: const Text('Warranty Claim')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _claim == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Warranty Claim')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error ?? 'Claim not found', style: const TextStyle(color: OwnlyTheme.danger)),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _loadClaim, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final claim = _claim!;
    final brand = claim.brandSupport;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Claim Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            tooltip: 'Update Status',
            onPressed: _updateStatusDialog,
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: OwnlyTheme.danger),
            tooltip: 'Withdraw Claim',
            onPressed: _deleteClaim,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Header Card
          Container(
            padding: const EdgeInsets.all(20),
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
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: _statusColor(claim.status).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        claim.status.toUpperCase(),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: _statusColor(claim.status),
                        ),
                      ),
                    ),
                    const Spacer(),
                    if (claim.claimReference != null)
                      Text(
                        'Ref: ${claim.claimReference}',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OwnlyTheme.muted),
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  claim.title,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                ),
                const SizedBox(height: 6),
                Text(
                  'Product: ${claim.productName}',
                  style: const TextStyle(fontSize: 14, color: OwnlyTheme.muted),
                ),
                if (claim.warrantyProvider != null)
                  Text(
                    'Coverage: ${claim.warrantyProvider}',
                    style: const TextStyle(fontSize: 13, color: OwnlyTheme.muted),
                  ),
                const SizedBox(height: 14),
                const Divider(height: 1),
                const SizedBox(height: 14),
                Row(
                  children: [
                    const Icon(Icons.calendar_today_outlined, size: 16, color: OwnlyTheme.muted),
                    const SizedBox(width: 6),
                    Text(
                      'Incident: ${df.format(claim.incidentDate)}',
                      style: const TextStyle(fontSize: 13, color: OwnlyTheme.ink),
                    ),
                    const Spacer(),
                    if (claim.claimCostCovered != null) ...[
                      const Icon(Icons.attach_money, size: 16, color: OwnlyTheme.success),
                      Text(
                        '\$${claim.claimCostCovered!.toStringAsFixed(2)} Covered',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: OwnlyTheme.success),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Problem Description Card
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE7EAF1)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Reported Problem Description',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                ),
                const SizedBox(height: 8),
                Text(
                  claim.issueDescription,
                  style: const TextStyle(fontSize: 14, color: OwnlyTheme.ink, height: 1.45),
                ),
                if (claim.resolutionNotes != null && claim.resolutionNotes!.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  const Divider(height: 1),
                  const SizedBox(height: 12),
                  const Text(
                    'Resolution & Support Notes',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: OwnlyTheme.success),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    claim.resolutionNotes!,
                    style: const TextStyle(fontSize: 13, color: OwnlyTheme.ink, height: 1.4),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Brand Support Channels
          if (brand != null) ...[
            Container(
              padding: const EdgeInsets.all(18),
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
                      const Icon(Icons.headset_mic_outlined, size: 20, color: OwnlyTheme.seed),
                      const SizedBox(width: 8),
                      Text(
                        'Official ${brand.brand} Support Channels',
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () {
                      Clipboard.setData(ClipboardData(text: brand.supportPhone));
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Copied ${brand.supportPhone} to clipboard')),
                      );
                    },
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF7F8FB),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.phone, size: 18, color: OwnlyTheme.seed),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  brand.supportPhone,
                                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                                ),
                                Text(
                                  brand.supportHours,
                                  style: const TextStyle(fontSize: 11, color: OwnlyTheme.muted),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.copy, size: 16, color: OwnlyTheme.muted),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  InkWell(
                    onTap: () {
                      Clipboard.setData(ClipboardData(text: brand.claimPortalUrl));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Copied warranty portal URL')),
                      );
                    },
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF7F8FB),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.language, size: 18, color: OwnlyTheme.seed),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Online Claim & RMA Portal',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                                ),
                                Text(
                                  brand.claimPortalUrl,
                                  style: const TextStyle(fontSize: 11, color: OwnlyTheme.muted),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.open_in_new, size: 16, color: OwnlyTheme.muted),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],

          // View / Export Claim Dossier
          ElevatedButton.icon(
            onPressed: _actionLoading ? null : _openDossier,
            icon: _actionLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.file_present_outlined, size: 20),
            label: const Text('View / Export Claim Dossier Packet'),
            style: ElevatedButton.styleFrom(
              backgroundColor: OwnlyTheme.seed,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              elevation: 0,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
