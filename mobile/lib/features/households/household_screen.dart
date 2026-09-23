import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/authentication/auth_controller.dart';

/// Screen for managing household vaults, members, roles, and invite codes.
class HouseholdScreen extends ConsumerStatefulWidget {
  const HouseholdScreen({super.key});

  @override
  ConsumerState<HouseholdScreen> createState() => _HouseholdScreenState();
}

class _HouseholdScreenState extends ConsumerState<HouseholdScreen> {
  bool _loading = true;
  String? _error;
  List<HouseholdItem> _households = [];
  String? _selectedHouseholdId;
  HouseholdDetailItem? _selectedDetail;
  bool _loadingDetail = false;

  @override
  void initState() {
    super.initState();
    _loadHouseholds();
  }

  Future<void> _loadHouseholds() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(householdRepositoryProvider);
      final list = await repo.listHouseholds();
      setState(() {
        _households = list;
        _loading = false;
        if (list.isNotEmpty) {
          _selectedHouseholdId ??= list.first.id;
        } else {
          _selectedHouseholdId = null;
          _selectedDetail = null;
        }
      });
      if (_selectedHouseholdId != null) {
        await _loadDetail(_selectedHouseholdId!);
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

  Future<void> _loadDetail(String id) async {
    setState(() => _loadingDetail = true);
    try {
      final repo = ref.read(householdRepositoryProvider);
      final detail = await repo.getHousehold(id);
      if (mounted) {
        setState(() {
          _selectedDetail = detail;
          _loadingDetail = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loadingDetail = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load household details: $e')),
        );
      }
    }
  }

  Future<void> _showCreateDialog() async {
    final controller = TextEditingController();
    final created = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create Household'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Household Name',
            hintText: 'e.g. Smith Residence, Vacation Home',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (created == true && controller.text.trim().isNotEmpty) {
      try {
        final repo = ref.read(householdRepositoryProvider);
        final item = await repo.createHousehold(controller.text.trim());
        _selectedHouseholdId = item.id;
        await _loadHouseholds();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Household "${item.name}" created!')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Creation failed: $e')),
          );
        }
      }
    }
  }

  Future<void> _showJoinDialog() async {
    final controller = TextEditingController();
    final joined = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Join Household'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter the 12-character invite code provided by the household admin.',
              style: TextStyle(color: OwnlyTheme.muted, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              autofocus: true,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Invite Code',
                hintText: 'OWN-XXXX-XXXX',
                prefixIcon: Icon(Icons.vpn_key_outlined),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Join'),
          ),
        ],
      ),
    );

    if (joined == true && controller.text.trim().isNotEmpty) {
      try {
        final repo = ref.read(householdRepositoryProvider);
        final detail = await repo.joinHousehold(controller.text.trim().toUpperCase());
        _selectedHouseholdId = detail.id;
        await _loadHouseholds();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Successfully joined "${detail.name}"!')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Join failed: $e')),
          );
        }
      }
    }
  }

  Future<void> _showInviteDialog() async {
    if (_selectedDetail == null) return;
    String selectedRole = 'member';
    int expiresInDays = 7;

    final invite = await showDialog<HouseholdInviteItem?>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Invite to Household'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Generate a secure invite code for "${_selectedDetail!.name}".',
                style: const TextStyle(color: OwnlyTheme.muted, fontSize: 13),
              ),
              const SizedBox(height: 16),
              const Text('Member Role', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                initialValue: selectedRole,
                items: const [
                  DropdownMenuItem(
                    value: 'member',
                    child: Text('Member (can add & edit shared products)'),
                  ),
                  DropdownMenuItem(
                    value: 'viewer',
                    child: Text('Viewer (read-only product & doc access)'),
                  ),
                ],
                onChanged: (v) {
                  if (v != null) setDialogState(() => selectedRole = v);
                },
              ),
              const SizedBox(height: 16),
              const Text('Valid For', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<int>(
                initialValue: expiresInDays,
                items: const [
                  DropdownMenuItem(value: 1, child: Text('1 day')),
                  DropdownMenuItem(value: 7, child: Text('7 days')),
                  DropdownMenuItem(value: 30, child: Text('30 days')),
                ],
                onChanged: (v) {
                  if (v != null) setDialogState(() => expiresInDays = v);
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, null),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () async {
                try {
                  final repo = ref.read(householdRepositoryProvider);
                  final item = await repo.createInvite(
                    _selectedDetail!.id,
                    role: selectedRole,
                    expiresInDays: expiresInDays,
                  );
                  if (context.mounted) Navigator.pop(ctx, item);
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed to generate invite: $e')),
                    );
                  }
                }
              },
              child: const Text('Generate Code'),
            ),
          ],
        ),
      ),
    );

    if (invite != null && mounted) {
      _showInviteCodeSheet(invite);
    }
  }

  void _showInviteCodeSheet(HouseholdInviteItem invite) {
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.mark_email_read_outlined, size: 48, color: OwnlyTheme.seed),
            const SizedBox(height: 12),
            const Text(
              'Invite Code Ready',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Share this code with your household member. It grants ${invite.role} access.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: OwnlyTheme.muted, fontSize: 14),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: OwnlyTheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: OwnlyTheme.seed.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    invite.code,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 2,
                      color: OwnlyTheme.seed,
                    ),
                  ),
                  const SizedBox(width: 12),
                  IconButton(
                    icon: const Icon(Icons.copy, color: OwnlyTheme.seed),
                    tooltip: 'Copy Code',
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: invite.code));
                      ScaffoldMessenger.of(ctx).showSnackBar(
                        const SnackBar(content: Text('Invite code copied to clipboard!')),
                      );
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Done'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _removeMember(HouseholdMemberItem member) async {
    if (_selectedDetail == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Remove ${member.userName}?'),
        content: Text('They will lose access to shared products in "${_selectedDetail!.name}".'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Remove', style: TextStyle(color: OwnlyTheme.danger)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final repo = ref.read(householdRepositoryProvider);
        await repo.removeMember(_selectedDetail!.id, member.userId);
        await _loadDetail(_selectedDetail!.id);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${member.userName} removed.')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to remove member: $e')),
          );
        }
      }
    }
  }

  Color _roleColor(String role) => switch (role) {
        'admin' => OwnlyTheme.seed,
        'member' => OwnlyTheme.success,
        'viewer' => OwnlyTheme.warning,
        _ => OwnlyTheme.muted,
      };

  @override
  Widget build(BuildContext context) {
    final authUser = ref.watch(authStateProvider).asData?.value;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Household Vaults'),
        actions: [
          IconButton(
            icon: const Icon(Icons.group_add_outlined),
            tooltip: 'Join with Code',
            onPressed: _showJoinDialog,
          ),
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Create Household',
            onPressed: _showCreateDialog,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: OwnlyTheme.danger),
                      const SizedBox(height: 12),
                      Text('Error: $_error'),
                      const SizedBox(height: 12),
                      FilledButton(onPressed: _loadHouseholds, child: const Text('Retry')),
                    ],
                  ),
                )
              : _households.isEmpty
                  ? _buildEmptyState()
                  : RefreshIndicator(
                      onRefresh: _loadHouseholds,
                      child: ListView(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        children: [
                          _buildHouseholdSelector(),
                          const SizedBox(height: 8),
                          if (_loadingDetail)
                            const Padding(
                              padding: EdgeInsets.all(32),
                              child: Center(child: CircularProgressIndicator()),
                            )
                          else if (_selectedDetail != null)
                            _buildHouseholdContent(authUser?.id),
                        ],
                      ),
                    ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.family_restroom, size: 64, color: OwnlyTheme.seed),
            const SizedBox(height: 16),
            const Text(
              'No Households Yet',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Create a household vault to securely share appliances, warranties, '
              'receipts, and manuals with family or roommates.',
              textAlign: TextAlign.center,
              style: TextStyle(color: OwnlyTheme.muted, fontSize: 14),
            ),
            const SizedBox(height: 24),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 48),
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                  ),
                  onPressed: _showJoinDialog,
                  icon: const Icon(Icons.vpn_key_outlined),
                  label: const Text('Join with Code'),
                ),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(0, 48),
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                  ),
                  onPressed: _showCreateDialog,
                  icon: const Icon(Icons.add),
                  label: const Text('Create Household'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHouseholdSelector() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          for (final h in _households)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text('${h.name} (${h.memberCount})'),
                selected: h.id == _selectedHouseholdId,
                onSelected: (selected) {
                  if (selected) {
                    setState(() => _selectedHouseholdId = h.id);
                    _loadDetail(h.id);
                  }
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHouseholdContent(String? currentUserId) {
    final detail = _selectedDetail!;
    final isAdmin = detail.role == 'admin';
    final canInvite = isAdmin || detail.role == 'member';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Household Overview Card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: OwnlyTheme.seed.withValues(alpha: 0.1),
                      child: const Icon(Icons.home_outlined, color: OwnlyTheme.seed, size: 24),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            detail.name,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${detail.productCount} shared products · ${detail.members.length} members',
                            style: const TextStyle(color: OwnlyTheme.muted, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                    Chip(
                      label: Text(
                        detail.role.toUpperCase(),
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: _roleColor(detail.role),
                        ),
                      ),
                      backgroundColor: _roleColor(detail.role).withValues(alpha: 0.1),
                      side: BorderSide(color: _roleColor(detail.role).withValues(alpha: 0.3)),
                    ),
                  ],
                ),
                if (canInvite) ...[
                  const Divider(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _showInviteDialog,
                          icon: const Icon(Icons.person_add_outlined, size: 18),
                          label: const Text('Invite Member'),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),

        const Padding(
          padding: EdgeInsets.fromLTRB(20, 16, 16, 8),
          child: Text(
            'Members',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OwnlyTheme.muted),
          ),
        ),

        // Members list
        Card(
          child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: detail.members.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, idx) {
              final m = detail.members[idx];
              final isSelf = m.userId == currentUserId;
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: _roleColor(m.role).withValues(alpha: 0.15),
                  child: Text(
                    m.userName.isNotEmpty ? m.userName[0].toUpperCase() : '?',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: _roleColor(m.role),
                    ),
                  ),
                ),
                title: Row(
                  children: [
                    Text(m.userName, style: const TextStyle(fontWeight: FontWeight.w600)),
                    if (isSelf) ...[
                      const SizedBox(width: 6),
                      const Text('(You)', style: TextStyle(color: OwnlyTheme.muted, fontSize: 12)),
                    ],
                  ],
                ),
                subtitle: Text(m.userEmail, style: const TextStyle(fontSize: 12)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Chip(
                      label: Text(
                        m.role,
                        style: TextStyle(fontSize: 11, color: _roleColor(m.role)),
                      ),
                      backgroundColor: _roleColor(m.role).withValues(alpha: 0.08),
                      padding: EdgeInsets.zero,
                    ),
                    if (isAdmin && !isSelf) ...[
                      const SizedBox(width: 4),
                      IconButton(
                        icon: const Icon(Icons.remove_circle_outline, size: 20, color: OwnlyTheme.danger),
                        tooltip: 'Remove Member',
                        onPressed: () => _removeMember(m),
                      ),
                    ],
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
