import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';

/// Modal dialog displaying the compiled Warranty Claim Dossier.
class ClaimDossierModal extends StatelessWidget {
  final ClaimDossierItem dossier;

  const ClaimDossierModal({super.key, required this.dossier});

  static void show(BuildContext context, ClaimDossierItem dossier) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => FractionallySizedBox(
        heightFactor: 0.9,
        child: ClaimDossierModal(dossier: dossier),
      ),
    );
  }

  void _copyToClipboard(BuildContext context) {
    Clipboard.setData(ClipboardData(text: dossier.formattedMarkdown));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Claim dossier copied to clipboard!'),
        backgroundColor: OwnlyTheme.success,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('MMM d, yyyy');
    final claim = dossier.claim;
    final prod = dossier.product;
    final w = dossier.warranty;
    final brand = dossier.brandSupport;

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Drag handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: OwnlyTheme.seed.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.folder_shared_outlined, color: OwnlyTheme.seed),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Warranty Claim Dossier',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: OwnlyTheme.ink),
                      ),
                      Text(
                        'Ref: ${claim.claimReference ?? "Pending"} • Generated ${df.format(dossier.generatedAt)}',
                        style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: OwnlyTheme.muted),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          // Content
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Product & Hardware Details
                _SectionCard(
                  title: '1. Product & Identification',
                  icon: Icons.devices_outlined,
                  children: [
                    _InfoRow(label: 'Product', value: prod['name']?.toString() ?? 'N/A'),
                    _InfoRow(label: 'Brand / OEM', value: prod['brand']?.toString() ?? 'N/A'),
                    _InfoRow(label: 'Model #', value: prod['model_number']?.toString() ?? 'N/A'),
                    _InfoRow(label: 'Serial Number', value: prod['serial_number']?.toString() ?? 'N/A', highlight: true),
                    if (prod['imei_number'] != null)
                      _InfoRow(label: 'IMEI / Device ID', value: prod['imei_number'].toString()),
                    _InfoRow(label: 'Purchase Date', value: prod['purchase_date']?.toString() ?? 'N/A'),
                    _InfoRow(label: 'Purchase Price', value: '${prod['currency'] ?? 'USD'} ${prod['purchase_price'] ?? 0.0}'),
                    _InfoRow(label: 'Seller', value: prod['seller']?.toString() ?? 'N/A'),
                  ],
                ),
                const SizedBox(height: 16),
                // Warranty Coverage
                _SectionCard(
                  title: '2. Warranty Verification',
                  icon: Icons.verified_user_outlined,
                  children: [
                    if (w != null) ...[
                      _InfoRow(label: 'Provider', value: w['provider']?.toString() ?? 'Manufacturer'),
                      _InfoRow(label: 'Type', value: '${(w['type']?.toString() ?? '').toUpperCase()} WARRANTY'),
                      _InfoRow(label: 'Valid Until', value: w['end_date']?.toString().substring(0, 10) ?? 'N/A'),
                      _InfoRow(
                        label: 'Status',
                        value: (w['status']?.toString() ?? 'ACTIVE').toUpperCase(),
                        statusColor: OwnlyTheme.success,
                      ),
                    ] else
                      const Text(
                        'No formal warranty certificate attached. Claim relies on implied merchantability.',
                        style: TextStyle(fontSize: 13, color: OwnlyTheme.muted, fontStyle: FontStyle.italic),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                // Incident & Issue
                _SectionCard(
                  title: '3. Reported Failure / Defect',
                  icon: Icons.error_outline,
                  children: [
                    _InfoRow(label: 'Issue Summary', value: claim.title, highlight: true),
                    _InfoRow(label: 'Incident Date', value: df.format(claim.incidentDate)),
                    const SizedBox(height: 8),
                    const Text('Problem Description:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OwnlyTheme.muted)),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF7F8FB),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        claim.issueDescription,
                        style: const TextStyle(fontSize: 13, color: OwnlyTheme.ink, height: 1.4),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Attached Documents
                _SectionCard(
                  title: '4. Verified Purchase Documents (${dossier.documents.length})',
                  icon: Icons.receipt_long_outlined,
                  children: [
                    if (dossier.documents.isEmpty)
                      const Text('No uploaded invoices or receipts on file.', style: TextStyle(fontSize: 13, color: OwnlyTheme.muted))
                    else
                      ...dossier.documents.map((d) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                const Icon(Icons.picture_as_pdf, size: 18, color: OwnlyTheme.danger),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    d['name']?.toString() ?? 'Invoice',
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: OwnlyTheme.seed.withValues(alpha: 0.08),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: const Text('Signed Link Included', style: TextStyle(fontSize: 10, color: OwnlyTheme.seed, fontWeight: FontWeight.w600)),
                                ),
                              ],
                            ),
                          )),
                  ],
                ),
                if (brand != null) ...[
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: '5. Manufacturer Support Channels',
                    icon: Icons.headset_mic_outlined,
                    children: [
                      _InfoRow(label: 'Support Hotline', value: brand.supportPhone, highlight: true),
                      _InfoRow(label: 'Claim Portal', value: brand.claimPortalUrl),
                      _InfoRow(label: 'Hours', value: brand.supportHours),
                    ],
                  ),
                ],
                const SizedBox(height: 20),
              ],
            ),
          ),
          // Bottom action button
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFE7EAF1))),
            ),
            child: ElevatedButton.icon(
              onPressed: () => _copyToClipboard(context),
              icon: const Icon(Icons.copy, size: 18),
              label: const Text('Copy Formatted Claim Dossier Markdown'),
              style: ElevatedButton.styleFrom(
                backgroundColor: OwnlyTheme.seed,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;

  const _SectionCard({required this.title, required this.icon, required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE7EAF1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: OwnlyTheme.seed),
              const SizedBox(width: 8),
              Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: OwnlyTheme.ink)),
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final bool highlight;
  final Color? statusColor;

  const _InfoRow({required this.label, required this.value, this.highlight = false, this.statusColor});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: const TextStyle(fontSize: 12, color: OwnlyTheme.muted)),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 13,
                fontWeight: highlight ? FontWeight.w700 : FontWeight.w500,
                color: statusColor ?? OwnlyTheme.ink,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
