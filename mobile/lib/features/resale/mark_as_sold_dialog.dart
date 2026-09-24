import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class MarkAsSoldDialog extends ConsumerStatefulWidget {
  final Product product;
  final ProductValuationItem valuation;

  const MarkAsSoldDialog({
    super.key,
    required this.product,
    required this.valuation,
  });

  @override
  ConsumerState<MarkAsSoldDialog> createState() => _MarkAsSoldDialogState();
}

class _MarkAsSoldDialogState extends ConsumerState<MarkAsSoldDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _priceCtrl;
  late final TextEditingController _notesCtrl;
  String _platform = 'eBay';
  late String _condition;
  late DateTime _saleDate;
  bool _submitting = false;

  final List<String> _platforms = [
    'eBay',
    'Facebook Marketplace',
    'Craigslist',
    'Swappa',
    'Private Sale',
    'Other',
  ];

  final List<String> _conditions = ['mint', 'excellent', 'good', 'fair', 'poor'];

  @override
  void initState() {
    super.initState();
    final defaultPrice = widget.valuation.estimatedResaleValue?.toStringAsFixed(2) ?? '';
    _priceCtrl = TextEditingController(text: defaultPrice);
    _notesCtrl = TextEditingController();
    _condition = widget.valuation.condition;
    _saleDate = DateTime.now();
  }

  @override
  void dispose() {
    _priceCtrl.dispose;
    _notesCtrl.dispose();
    super.dispose();
  }

  double? get _currentInputPrice => double.tryParse(_priceCtrl.text);

  double? get _realizedNetCost {
    final price = _currentInputPrice;
    if (price == null) return null;
    final original = widget.product.purchasePrice?.toDouble() ?? 0.0;
    return original + widget.valuation.totalRepairsCost - price;
  }

  double? get _costPerDay {
    final net = _realizedNetCost;
    if (net == null || widget.valuation.daysOwned <= 0) return null;
    return net / widget.valuation.daysOwned;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final price = double.tryParse(_priceCtrl.text);
    if (price == null || price < 0) return;

    setState(() => _submitting = true);
    try {
      await ref.read(resaleRepositoryProvider).sellProduct(
            widget.product.id,
            resalePrice: price,
            resaleDate: _saleDate,
            resalePlatform: _platform,
            resaleNotes: _notesCtrl.text.trim().isNotEmpty ? _notesCtrl.text.trim() : null,
            condition: _condition,
          );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to record sale: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: OwnlyColors.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.monetization_on_outlined, color: OwnlyColors.emerald, size: 24),
                    const SizedBox(width: 10),
                    const Text(
                      'Record Product Sale',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: OwnlyColors.textPrimary,
                      ),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Item: ${widget.product.name}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: OwnlyColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 16),

                // Sale Price Field
                TextFormField(
                  controller: _priceCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Selling Price (USD)',
                    prefixText: '\$ ',
                    hintText: '0.00',
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Please enter sale price';
                    final parsed = double.tryParse(v);
                    if (parsed == null || parsed < 0) return 'Must be a valid positive amount';
                    return null;
                  },
                  onChanged: (_) => setState(() {}),
                ),
                const SizedBox(height: 12),

                // Net Cost of Ownership Feedback Banner
                if (_realizedNetCost != null)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: OwnlyColors.emerald.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: OwnlyColors.emerald.withValues(alpha: 0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.analytics_outlined, color: OwnlyColors.emerald, size: 16),
                            SizedBox(width: 6),
                            Text(
                              'Realized Net Cost of Ownership',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: OwnlyColors.emerald,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '\$${_realizedNetCost!.toStringAsFixed(2)} net cost  •  \$${_costPerDay?.toStringAsFixed(2) ?? '0.00'}/day over ${widget.valuation.daysOwned} days',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: OwnlyColors.textPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),

                // Platform Dropdown
                DropdownButtonFormField<String>(
                  initialValue: _platform,
                  decoration: const InputDecoration(labelText: 'Selling Platform'),
                  items: _platforms
                      .map((p) => DropdownMenuItem(value: p, child: Text(p)))
                      .toList(),
                  onChanged: (v) => setState(() => _platform = v ?? 'eBay'),
                ),
                const SizedBox(height: 16),

                // Condition Dropdown
                DropdownButtonFormField<String>(
                  initialValue: _condition,
                  decoration: const InputDecoration(labelText: 'Condition at Sale'),
                  items: _conditions
                      .map((c) => DropdownMenuItem(
                            value: c,
                            child: Text(c.toUpperCase()),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _condition = v ?? 'good'),
                ),
                const SizedBox(height: 16),

                // Notes Field
                TextFormField(
                  controller: _notesCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Sale Notes (Optional)',
                    hintText: 'Buyer details, tracking ID, or notes',
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 24),

                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: OwnlyColors.emerald,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: _submitting ? null : _submit,
                      child: _submitting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Finalize Sale'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
