import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';

class ResaleListingModal extends StatelessWidget {
  final ResaleListingPacketItem packet;

  const ResaleListingModal({super.key, required this.packet});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: OwnlyColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        children: [
          // Drag handle
          Container(
            margin: const EdgeInsets.only(top: 12, bottom: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: OwnlyColors.border,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              children: [
                const Icon(Icons.storefront, color: OwnlyColors.emerald, size: 24),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Marketplace Resale Listing',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: OwnlyColors.textPrimary,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: OwnlyColors.textSecondary),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: OwnlyColors.border),

          // Scrollable body
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Listing Title
                Text(
                  packet.title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: OwnlyColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),

                // Suggested Price Card
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: OwnlyColors.card,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: OwnlyColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'SUGGESTED ASKING PRICE',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: OwnlyColors.textSecondary,
                              letterSpacing: 0.5,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: OwnlyColors.emerald.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              packet.condition.toUpperCase(),
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
                        packet.suggestedPrice != null
                            ? '\$${packet.suggestedPrice!.toStringAsFixed(2)} USD'
                            : 'Best Offer',
                        style: const TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w900,
                          color: OwnlyColors.textPrimary,
                        ),
                      ),
                      if (packet.suggestedPriceRange != null) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Estimated Range: \$${packet.suggestedPriceRange!.low.toStringAsFixed(0)} (quick sale) – \$${packet.suggestedPriceRange!.high.toStringAsFixed(0)} (patient)',
                          style: const TextStyle(fontSize: 12, color: OwnlyColors.textSecondary),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Copy Action Buttons
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.copy, size: 16),
                        label: const Text('Copy Markdown'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: OwnlyColors.emerald,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: packet.formattedMarkdown));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Markdown copied! Ready for eBay/Forums.')),
                          );
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.text_fields, size: 16),
                        label: const Text('Copy Plain Text'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: OwnlyColors.textPrimary,
                          side: const BorderSide(color: OwnlyColors.border),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: packet.plainTextDescription));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Plain text copied for Facebook/Craigslist!')),
                          );
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Specifications Box
                const Text(
                  'Item Specifications',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: OwnlyColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: OwnlyColors.card,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: OwnlyColors.border),
                  ),
                  child: Column(
                    children: packet.specifications.entries.map((entry) {
                      final keyDisplay = entry.key
                          .replaceAll('_', ' ')
                          .split(' ')
                          .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
                          .join(' ');
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 140,
                              child: Text(
                                keyDisplay,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: OwnlyColors.textSecondary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                entry.value.toString(),
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: OwnlyColors.textPrimary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ),
                if (packet.repairHistory.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  const Text(
                    'Verified Repair & Maintenance History',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: OwnlyColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...packet.repairHistory.map((r) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: OwnlyColors.card,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: OwnlyColors.border),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.build_circle_outlined, color: OwnlyColors.emerald, size: 18),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    r.repairVendor ?? r.description ?? 'Repair',
                                    style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold,
                                      color: OwnlyColors.textPrimary,
                                    ),
                                  ),
                                  if (r.description != null && r.repairVendor != null)
                                    Text(
                                      r.description!,
                                      style: const TextStyle(fontSize: 11, color: OwnlyColors.textSecondary),
                                    ),
                                ],
                              ),
                            ),
                            if (r.cost != null)
                              Text(
                                '\$${r.cost!.toStringAsFixed(2)}',
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OwnlyColors.textPrimary),
                              ),
                          ],
                        ),
                      )),
                ],
                const SizedBox(height: 20),

                // Verified Receipts Proof
                const Text(
                  'Verified Purchase & Authenticity Proof',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: OwnlyColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                if (packet.verifiedDocuments.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: OwnlyColors.card,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: OwnlyColors.border),
                    ),
                    child: const Text(
                      'No attached receipts for this item.',
                      style: TextStyle(fontSize: 12, color: OwnlyColors.textSecondary),
                    ),
                  )
                else
                  ...packet.verifiedDocuments.map((doc) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: OwnlyColors.card,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: OwnlyColors.border),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.verified, color: OwnlyColors.emerald, size: 18),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    doc.name,
                                    style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold,
                                      color: OwnlyColors.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    doc.type.toUpperCase(),
                                    style: const TextStyle(fontSize: 10, color: OwnlyColors.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.lock_outline, size: 14, color: OwnlyColors.textSecondary),
                          ],
                        ),
                      )),
                const SizedBox(height: 20),

                // Preview Box
                const Text(
                  'Listing Preview (Markdown)',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: OwnlyColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: OwnlyColors.card,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: OwnlyColors.border),
                  ),
                  child: Text(
                    packet.formattedMarkdown,
                    style: const TextStyle(
                      fontSize: 12,
                      fontFamily: 'monospace',
                      color: OwnlyColors.textPrimary,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
