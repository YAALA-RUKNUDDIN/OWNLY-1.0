import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';

import 'package:ownly/core/constants/categories.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/products/products_controller.dart';
import 'package:ownly/features/products/repairs_tab.dart';

/// Product detail: overview, timeline, documents, warranty, repairs sections.
class ProductDetailScreen extends ConsumerStatefulWidget {
  final String productId;
  const ProductDetailScreen({super.key, required this.productId});

  @override
  ConsumerState<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends ConsumerState<ProductDetailScreen> {
  @override
  Widget build(BuildContext context) {
    final state = ref.watch(productDetailProvider(widget.productId));
    final p = state.product;

    return Scaffold(
      appBar: AppBar(
        title: Text(p?.name ?? 'Product'),
        actions: [
          if (p != null)
            IconButton(
              icon: Icon(p.isShared ? Icons.folder_shared : Icons.share_outlined),
              tooltip: p.isShared ? 'Shared with household' : 'Share with household',
              onPressed: () => _showShareDialog(context, p),
            ),
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Delete product',
            onPressed: () => _confirmDelete(context),
          ),
        ],
      ),
      body: state.loading && p == null
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? Center(child: Text(state.error!))
              : DefaultTabController(
                  length: 4,
                  child: Column(
                    children: [
                      // Header
                      Container(
                        width: double.infinity,
                        color: Colors.white,
                        padding: const EdgeInsets.all(20),
                        child: Row(
                          children: [
                            CircleAvatar(
                              radius: 30,
                              backgroundColor: OwnlyTheme.seed.withValues(alpha: 0.1),
                              child: Icon(categoryIcon(p!.category),
                                  color: OwnlyTheme.seed, size: 28),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(p.name,
                                      style: const TextStyle(
                                          fontSize: 20, fontWeight: FontWeight.w800)),
                                  if (p.brand != null)
                                    Text(p.brand!,
                                        style: const TextStyle(color: OwnlyTheme.muted)),
                                  const SizedBox(height: 6),
                                  Wrap(
                                    spacing: 8,
                                    crossAxisAlignment: WrapCrossAlignment.center,
                                    children: [
                                      _WarrantyBadge(warranty: p.warranty),
                                      if (p.isShared)
                                        Chip(
                                          avatar: const Icon(Icons.folder_shared, size: 14, color: OwnlyTheme.seed),
                                          label: const Text('Shared',
                                              style: TextStyle(
                                                  fontSize: 11,
                                                  color: OwnlyTheme.seed,
                                                  fontWeight: FontWeight.bold)),
                                          backgroundColor: OwnlyTheme.seed.withValues(alpha: 0.1),
                                          side: BorderSide(color: OwnlyTheme.seed.withValues(alpha: 0.3)),
                                          padding: EdgeInsets.zero,
                                        ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const TabBar(
                        labelColor: OwnlyTheme.seed,
                        indicatorColor: OwnlyTheme.seed,
                        tabs: [
                          Tab(text: 'Overview'),
                          Tab(text: 'Timeline'),
                          Tab(text: 'Documents'),
                          Tab(text: 'Repairs'),
                        ],
                      ),
                      Expanded(
                        child: TabBarView(children: [
                          _OverviewTab(state: state),
                          _TimelineTab(events: state.timeline),
                          _DocumentsTab(productId: widget.productId, documents: state.documents),
                          RepairsTab(productId: widget.productId, currency: p.currency),
                        ]),
                      ),
                    ],
                  ),
                ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete product?'),
        content: const Text(
            'This removes the product and its records from your vault. '
            'Documents are permanently deleted.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete', style: TextStyle(color: OwnlyTheme.danger)),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await ref.read(productDetailProvider(widget.productId).notifier).deleteProduct();
      if (context.mounted) Navigator.of(context).pop(true);
    }
  }

  Future<void> _showShareDialog(BuildContext context, Product product) async {
    try {
      final repo = ref.read(householdRepositoryProvider);
      final households = await repo.listHouseholds();
      if (!context.mounted) return;
      if (households.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'No households found. Create a household first in Profile > Household & family sharing.',
            ),
          ),
        );
        return;
      }

      final selectedHouseholdId = await showDialog<String?>(
        context: context,
        builder: (ctx) => SimpleDialog(
          title: const Text('Share with Household Vault'),
          children: [
            SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, 'personal'),
              child: const Row(
                children: [
                  Icon(Icons.lock_outline, color: OwnlyTheme.muted),
                  SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Personal Vault', style: TextStyle(fontWeight: FontWeight.w600)),
                      Text('Only visible to you', style: TextStyle(color: OwnlyTheme.muted, fontSize: 12)),
                    ],
                  ),
                ],
              ),
            ),
            const Divider(),
            for (final h in households)
              SimpleDialogOption(
                onPressed: () => Navigator.pop(ctx, h.id),
                child: Row(
                  children: [
                    const Icon(Icons.home_outlined, color: OwnlyTheme.seed),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(h.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                        Text('${h.memberCount} members · ${h.role}',
                            style: const TextStyle(color: OwnlyTheme.muted, fontSize: 12)),
                      ],
                    ),
                  ],
                ),
              ),
          ],
        ),
      );

      if (selectedHouseholdId != null) {
        final targetHousehold = selectedHouseholdId == 'personal' ? null : selectedHouseholdId;
        await repo.shareProduct(product.id, targetHousehold);
        ref.read(productDetailProvider(widget.productId).notifier).load();
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                targetHousehold == null
                    ? 'Product moved to personal vault.'
                    : 'Product shared with household!',
              ),
            ),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sharing failed: $e')),
        );
      }
    }
  }
}

class _WarrantyBadge extends StatelessWidget {
  final WarrantyInfo warranty;
  const _WarrantyBadge({required this.warranty});

  @override
  Widget build(BuildContext context) {
    final color = statusColor(warranty.status);
    final extra = warranty.daysRemaining != null && warranty.status != 'none'
        ? ' · ${Formatters.daysRemaining(warranty.daysRemaining!)}'
        : '';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        'Warranty: ${statusLabel(warranty.status)}$extra',
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color),
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  final ProductDetailState state;
  const _OverviewTab({required this.state});

  @override
  Widget build(BuildContext context) {
    final p = state.product!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _InfoRow('Purchase date', Formatters.date(p.purchaseDate)),
        _InfoRow('Purchase price', Formatters.money(p.purchasePrice, p.currency)),
        if (p.seller != null) _InfoRow('Seller', p.seller!),
        if (p.modelNumber != null) _InfoRow('Model', p.modelNumber!),
        if (p.serialNumber != null) _InfoRow('Serial number', p.serialNumber!),
        if (p.returnWindow.tracked)
          _InfoRow(
            'Return window',
            p.returnWindow.endDate == null
                ? '—'
                : '${Formatters.date(p.returnWindow.endDate!)} · '
                    'closes ${Formatters.daysRemaining(p.returnWindow.daysRemaining ?? 0)}',
          ),
        _InfoRow('Status', p.status),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label, style: const TextStyle(color: OwnlyTheme.muted)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}

class _TimelineTab extends StatelessWidget {
  final List<TimelineEvent> events;
  const _TimelineTab({required this.events});

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return const Center(child: Text('No events yet.', style: TextStyle(color: OwnlyTheme.muted)));
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: events.length,
      itemBuilder: (context, i) {
        final isLast = i == events.length - 1;
        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Column(
                children: [
                  Container(
                    width: 12, height: 12,
                    decoration: const BoxDecoration(
                      color: OwnlyTheme.seed, shape: BoxShape.circle,
                    ),
                  ),
                  if (!isLast)
                    Expanded(child: Container(width: 2, color: const Color(0xFFE1E5EE))),
                ],
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(events[i].title,
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text(Formatters.date(events[i].eventDate),
                          style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted)),
                      if (events[i].description != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(events[i].description!,
                              style: const TextStyle(fontSize: 13)),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _DocumentsTab extends ConsumerWidget {
  final String productId;
  final List<DocumentFile> documents;
  const _DocumentsTab({required this.productId, required this.documents});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Stack(
      children: [
        documents.isEmpty
            ? const Center(
                child: Text('No documents yet.\nAdd your invoice to keep it safe.',
                    textAlign: TextAlign.center, style: TextStyle(color: OwnlyTheme.muted)))
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: documents.length,
                itemBuilder: (context, i) {
                  final doc = documents[i];
                  return Card(
                    child: ListTile(
                      leading: Icon(
                        doc.mimeType == 'application/pdf'
                            ? Icons.picture_as_pdf_outlined
                            : Icons.image_outlined,
                        color: OwnlyTheme.seed,
                      ),
                      title: Text(doc.documentName),
                      subtitle: Text(
                          '${doc.documentType.replaceAll('_', ' ')} · '
                          '${(doc.fileSize / 1024).toStringAsFixed(0)} KB'),
                      trailing: IconButton(
                        icon: const Icon(Icons.download_outlined),
                        onPressed: () async {
                          try {
                            final url = await ref
                                .read(repositoryProvider)
                                .documentDownloadUrl(doc.id);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Secure link ready: $url')));
                            }
                          } catch (e) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Download failed: $e')));
                            }
                          }
                        },
                      ),
                    ),
                  );
                },
              ),
        Positioned(
          right: 16, bottom: 16,
          child: FloatingActionButton.extended(
            onPressed: () => _upload(context, ref),
            icon: const Icon(Icons.upload_file),
            label: const Text('Add document'),
          ),
        ),
      ],
    );
  }

  Future<void> _upload(BuildContext context, WidgetRef ref) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom, allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png', 'webp'],
    );
    if (result == null || result.files.single.path == null) return;
    try {
      await ref.read(repositoryProvider).uploadDocument(
          productId, result.files.single.path!, result.files.single.name, 'other');
      ref.read(productDetailProvider(productId).notifier).load();
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Upload failed: $e')));
      }
    }
  }
}
