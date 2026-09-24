import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/resale/mark_as_disposed_dialog.dart';
import 'package:ownly/features/resale/mark_as_sold_dialog.dart';
import 'package:ownly/features/resale/resale_listing_modal.dart';

class ResaleTab extends ConsumerStatefulWidget {
  final Product product;
  final VoidCallback? onProductUpdated;

  const ResaleTab({super.key, required this.product, this.onProductUpdated});

  @override
  ConsumerState<ResaleTab> createState() => _ResaleTabState();
}

class _ResaleTabState extends ConsumerState<ResaleTab> {
  late Future<ProductValuationItem> _valuationFuture;
  bool _generatingPacket = false;

  @override
  void initState() {
    super.initState();
    _loadValuation();
  }

  void _loadValuation() {
    _valuationFuture = ref.read(resaleRepositoryProvider).getValuation(widget.product.id);
  }

  Future<void> _changeCondition(String condition) async {
    try {
      await ref.read(resaleRepositoryProvider).updateCondition(widget.product.id, condition);
      setState(() => _loadValuation());
      widget.onProductUpdated?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update condition: $e')),
        );
      }
    }
  }

  Future<void> _openResalePacket() async {
    setState(() => _generatingPacket = true);
    try {
      final packet = await ref.read(resaleRepositoryProvider).getResalePacket(widget.product.id);
      if (mounted) {
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (ctx) => ResaleListingModal(packet: packet),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to generate resale packet: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _generatingPacket = false);
    }
  }

  Future<void> _openMarkAsSold(ProductValuationItem valuation) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => MarkAsSoldDialog(
        product: widget.product,
        valuation: valuation,
      ),
    );
    if (result == true) {
      setState(() => _loadValuation());
      widget.onProductUpdated?.call();
    }
  }

  Future<void> _openMarkAsDisposed() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => MarkAsDisposedDialog(product: widget.product),
    );
    if (result == true) {
      setState(() => _loadValuation());
      widget.onProductUpdated?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<ProductValuationItem>(
      future: _valuationFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 40, color: OwnlyColors.error),
                  const SizedBox(height: 12),
                  Text('Failed to calculate valuation: ${snapshot.error}', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  ElevatedButton(onPressed: () => setState(() => _loadValuation()), child: const Text('Retry')),
                ],
              ),
            ),
          );
        }

        final val = snapshot.data!;
        final isSold = val.isSold;
        final isDisposed = widget.product.status == 'recycled' || widget.product.status == 'donated';

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Status Header Banner
            if (isSold)
              _buildSoldBanner(val)
            else if (isDisposed)
              _buildDisposedBanner()
            else
              _buildActiveValuationCard(val),

            const SizedBox(height: 20),

            // Condition testing row
            if (!isSold && !isDisposed) ...[
              const Text(
                'Product Condition & Quality',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: ['mint', 'excellent', 'good', 'fair', 'poor'].map((c) {
                    final isSelected = val.condition.toLowerCase() == c;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(c.toUpperCase()),
                        selected: isSelected,
                        selectedColor: OwnlyColors.emerald.withValues(alpha: 0.2),
                        labelStyle: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isSelected ? OwnlyColors.emerald : OwnlyColors.textSecondary,
                        ),
                        onSelected: (selected) {
                          if (selected && !isSelected) {
                            _changeCondition(c);
                          }
                        },
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Action Buttons
            if (!isSold && !isDisposed) ...[
              ElevatedButton.icon(
                icon: _generatingPacket
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.storefront_outlined),
                label: const Text('Generate Marketplace Resale Listing'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: OwnlyColors.emerald,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: _generatingPacket ? null : _openResalePacket,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.monetization_on_outlined, size: 16),
                      label: const Text('Mark as Sold'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: OwnlyColors.emerald,
                        side: const BorderSide(color: OwnlyColors.emerald),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () => _openMarkAsSold(val),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.recycling_outlined, size: 16),
                      label: const Text('Recycle / Donate'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: OwnlyColors.textSecondary,
                        side: const BorderSide(color: OwnlyColors.border),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: _openMarkAsDisposed,
                    ),
                  ),
                ],
              ),
            ],

            const SizedBox(height: 24),

            // Ownership Breakdown Card
            _buildOwnershipBreakdownCard(val),
          ],
        );
      },
    );
  }

  Widget _buildActiveValuationCard(ProductValuationItem val) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: OwnlyColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: OwnlyColors.emerald.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: OwnlyColors.emerald.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'ESTIMATED RESALE VALUE',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: OwnlyColors.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: OwnlyColors.emerald.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '${val.valueRetentionPercent?.toStringAsFixed(1) ?? '0.0'}% RETAINED',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: OwnlyColors.emerald,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            val.estimatedResaleValue != null
                ? '\$${val.estimatedResaleValue!.toStringAsFixed(2)} USD'
                : 'Market estimate unavailable',
            style: const TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.w900,
              color: OwnlyColors.textPrimary,
            ),
          ),
          if (val.suggestedListingPriceRange != null) ...[
            const SizedBox(height: 6),
            Text(
              'Market Range: \$${val.suggestedListingPriceRange!.low.toStringAsFixed(0)} (fast sale) – \$${val.suggestedListingPriceRange!.high.toStringAsFixed(0)} (top condition)',
              style: const TextStyle(fontSize: 12, color: OwnlyColors.textSecondary),
            ),
          ],
          const Divider(height: 24, color: OwnlyColors.border),
          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  'Net Cost to Date',
                  val.netCostOfOwnership != null ? '\$${val.netCostOfOwnership!.toStringAsFixed(2)}' : 'N/A',
                ),
              ),
              Expanded(
                child: _buildMetricTile(
                  'Cost / Day Owned',
                  val.costPerDay != null ? '\$${val.costPerDay!.toStringAsFixed(2)}/day' : 'N/A',
                ),
              ),
              Expanded(
                child: _buildMetricTile(
                  'Days Owned',
                  '${val.daysOwned} days',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSoldBanner(ProductValuationItem val) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: OwnlyColors.emerald.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: OwnlyColors.emerald.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: OwnlyColors.emerald, size: 24),
              const SizedBox(width: 8),
              const Text(
                'PRODUCT SOLD',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: OwnlyColors.emerald,
                  letterSpacing: 0.5,
                ),
              ),
              const Spacer(),
              if (widget.product.resalePlatform != null)
                Text(
                  widget.product.resalePlatform!,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OwnlyColors.textSecondary),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            val.actualResalePrice != null
                ? 'Sold for \$${val.actualResalePrice!.toStringAsFixed(2)} USD'
                : 'Sold',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary),
          ),
          const SizedBox(height: 6),
          Text(
            'Final Net Cost of Ownership: \$${val.realizedNetCost?.toStringAsFixed(2) ?? '0.00'}  (\$${val.costPerDay?.toStringAsFixed(2) ?? '0.00'}/day)',
            style: const TextStyle(fontSize: 13, color: OwnlyColors.textPrimary, fontWeight: FontWeight.w500),
          ),
          if (widget.product.resaleNotes != null && widget.product.resaleNotes!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Notes: ${widget.product.resaleNotes}',
              style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: OwnlyColors.textSecondary),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDisposedBanner() {
    final statusName = widget.product.status == 'recycled' ? 'Recycled' : 'Donated';
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: OwnlyColors.card,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: OwnlyColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.recycling, color: OwnlyColors.emerald, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Item $statusName',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary),
                ),
                const Text(
                  'Logged in digital ownership archive. Responsible exit complete.',
                  style: TextStyle(fontSize: 12, color: OwnlyColors.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOwnershipBreakdownCard(ProductValuationItem val) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: OwnlyColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: OwnlyColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Total Cost of Ownership (TCO) Breakdown',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary),
          ),
          const SizedBox(height: 12),
          _buildBreakdownRow(
            'Original Purchase Price',
            val.purchasePrice != null ? '\$${val.purchasePrice!.toStringAsFixed(2)}' : 'Not recorded',
          ),
          _buildBreakdownRow(
            'Total Maintenance & Repairs',
            '+\$${val.totalRepairsCost.toStringAsFixed(2)}',
          ),
          _buildBreakdownRow(
            val.isSold ? 'Realized Sale Price' : 'Estimated Current Resale',
            val.isSold
                ? '-\$${val.actualResalePrice?.toStringAsFixed(2) ?? '0.00'}'
                : '-\$${val.estimatedResaleValue?.toStringAsFixed(2) ?? '0.00'}',
            highlightColor: OwnlyColors.emerald,
          ),
          const Divider(height: 16, color: OwnlyColors.border),
          _buildBreakdownRow(
            'Net Ownership Cost',
            val.netCostOfOwnership != null ? '\$${val.netCostOfOwnership!.toStringAsFixed(2)}' : 'N/A',
            isBold: true,
          ),
        ],
      ),
    );
  }

  Widget _buildMetricTile(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: OwnlyColors.textSecondary)),
        const SizedBox(height: 3),
        Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary)),
      ],
    );
  }

  Widget _buildBreakdownRow(String label, String value, {bool isBold = false, Color? highlightColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
              color: isBold ? OwnlyColors.textPrimary : OwnlyColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
              color: highlightColor ?? (isBold ? OwnlyColors.textPrimary : OwnlyColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}
