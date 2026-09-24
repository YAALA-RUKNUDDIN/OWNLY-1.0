import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

/// Screen listing all user warranty claims with status filters.
class ClaimsScreen extends ConsumerStatefulWidget {
  const ClaimsScreen({super.key});

  @override
  ConsumerState<ClaimsScreen> createState() => _ClaimsScreenState();
}

class _ClaimsScreenState extends ConsumerState<ClaimsScreen> {
  bool _loading = true;
  String? _error;
  List<WarrantyClaimItem> _claims = [];
  String? _selectedFilter; // null = all

  @override
  void initState() {
    super.initState();
    _loadClaims();
  }

  Future<void> _loadClaims() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(claimRepositoryProvider);
      final list = await repo.listClaims(status: _selectedFilter);
      if (mounted) {
        setState(() {
          _claims = list;
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

    final filters = [
      {'label': 'All Claims', 'value': null},
      {'label': 'Draft', 'value': 'draft'},
      {'label': 'Submitted', 'value': 'submitted'},
      {'label': 'In Review', 'value': 'in_review'},
      {'label': 'Approved', 'value': 'approved'},
      {'label': 'Closed', 'value': 'closed'},
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Warranty Claims'),
      ),
      body: Column(
        children: [
          // Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: filters.map((f) {
                final isSelected = _selectedFilter == f['value'];
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(f['label'] as String),
                    selected: isSelected,
                    selectedColor: OwnlyTheme.seed.withValues(alpha: 0.12),
                    checkmarkColor: OwnlyTheme.seed,
                    labelStyle: TextStyle(
                      color: isSelected ? OwnlyTheme.seed : OwnlyTheme.ink,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                      fontSize: 13,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                      side: BorderSide(
                        color: isSelected ? OwnlyTheme.seed : const Color(0xFFE1E5EE),
                      ),
                    ),
                    onSelected: (val) {
                      setState(() => _selectedFilter = f['value']);
                      _loadClaims();
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const Divider(height: 1),
          // Content
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(_error!, style: const TextStyle(color: OwnlyTheme.danger)),
                            const SizedBox(height: 12),
                            ElevatedButton(onPressed: _loadClaims, child: const Text('Retry')),
                          ],
                        ),
                      )
                    : _claims.isEmpty
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.all(32),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(18),
                                    decoration: BoxDecoration(
                                      color: OwnlyTheme.seed.withValues(alpha: 0.08),
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(Icons.assignment_turned_in_outlined,
                                        size: 40, color: OwnlyTheme.seed),
                                  ),
                                  const SizedBox(height: 16),
                                  const Text(
                                    'No Warranty Claims Found',
                                    style: TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.w700,
                                      color: OwnlyTheme.ink,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  const Text(
                                    'When you encounter a defect or failure with an item, file a claim from its product detail page to track repairs and generate claim dossiers.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(fontSize: 13, color: OwnlyTheme.muted, height: 1.4),
                                  ),
                                ],
                              ),
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: _loadClaims,
                            child: ListView.builder(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              itemCount: _claims.length,
                              itemBuilder: (ctx, i) {
                                final claim = _claims[i];
                                return Card(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  child: InkWell(
                                    onTap: () async {
                                      await context.push('/claims/${claim.id}');
                                      _loadClaims();
                                    },
                                    borderRadius: BorderRadius.circular(16),
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  claim.title,
                                                  style: const TextStyle(
                                                    fontSize: 15,
                                                    fontWeight: FontWeight.w700,
                                                    color: OwnlyTheme.ink,
                                                  ),
                                                ),
                                              ),
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
                                            ],
                                          ),
                                          const SizedBox(height: 6),
                                          Text(
                                            'Product: ${claim.productName}',
                                            style: const TextStyle(fontSize: 13, color: OwnlyTheme.muted),
                                          ),
                                          const SizedBox(height: 10),
                                          Row(
                                            children: [
                                              const Icon(Icons.calendar_today_outlined, size: 14, color: OwnlyTheme.muted),
                                              const SizedBox(width: 4),
                                              Text(
                                                df.format(claim.incidentDate),
                                                style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                                              ),
                                              const Spacer(),
                                              if (claim.claimReference != null)
                                                Text(
                                                  'Ref: ${claim.claimReference}',
                                                  style: const TextStyle(
                                                    fontSize: 12,
                                                    fontWeight: FontWeight.w600,
                                                    color: OwnlyTheme.ink,
                                                  ),
                                                ),
                                              const SizedBox(width: 4),
                                              const Icon(Icons.chevron_right, size: 18, color: OwnlyTheme.muted),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}
