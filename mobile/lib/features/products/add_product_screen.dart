import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import 'package:ownly/core/constants/categories.dart';
import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/products/products_controller.dart';

/// Add-product wizard. Method A: manual entry. Method B/C: photo → OCR →
/// editable draft → user confirmation. OCR data is NEVER auto-saved: the
/// user reviews and edits every extracted field before saving.
class AddProductScreen extends ConsumerStatefulWidget {
  const AddProductScreen({super.key});

  @override
  ConsumerState<AddProductScreen> createState() => _AddProductScreenState();
}

class _AddProductScreenState extends ConsumerState<AddProductScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _brand = TextEditingController();
  final _model = TextEditingController();
  final _seller = TextEditingController();
  final _price = TextEditingController();
  final _serial = TextEditingController();
  DateTime _purchaseDate = DateTime.now();
  String _category = 'electronics';
  int _returnDays = 0;
  int? _warrantyMonths;
  bool _saving = false;
  bool _ocrRunning = false;
  String? _error;
  OcrDraft? _draft;

  @override
  void dispose() {
    _name.dispose(); _brand.dispose(); _model.dispose();
    _seller.dispose(); _price.dispose(); _serial.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _purchaseDate,
      firstDate: DateTime(1990),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _purchaseDate = picked);
  }

  Future<void> _scanReceipt() async {
    final picker = ImagePicker();
    final photo = await picker.pickImage(
      source: ImageSource.camera, maxWidth: 2048, imageQuality: 85,
    );
    if (photo == null) return;
    setState(() { _ocrRunning = true; _error = null; });
    try {
      final draft = await ref.read(repositoryProvider).ocrExtract(photo.path);
      _applyDraft(draft, count: 1);
    } on ApiException catch (e) {
      setState(() { _ocrRunning = false; _error = e.message; });
    } catch (e) {
      setState(() { _ocrRunning = false; _error = 'Scan failed: $e'; });
    }
  }

  /// Gallery path: pick one or more images, OCR each, keep the most
  /// confident draft. Nothing is saved until the user confirms (spec Rule 5).
  Future<void> _pickFromGallery() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(maxWidth: 2048, imageQuality: 85);
    if (images.isEmpty) return;
    setState(() { _ocrRunning = true; _error = null; });
    try {
      final repo = ref.read(repositoryProvider);
      OcrDraft? best;
      for (final image in images) {
        final draft = await repo.ocrExtract(image.path);
        if (best == null || draft.confidence > best.confidence) best = draft;
      }
      _applyDraft(best!, count: images.length);
    } on ApiException catch (e) {
      setState(() { _ocrRunning = false; _error = e.message; });
    } catch (e) {
      setState(() { _ocrRunning = false; _error = 'Scan failed: $e'; });
    }
  }

  /// Pre-fill the form from an OCR draft — the user reviews/edits before
  /// saving; OCR data is NEVER auto-saved (spec Rule 5).
  void _applyDraft(OcrDraft draft, {required int count}) {
    setState(() {
      _draft = draft;
      _ocrRunning = false;
      if (draft.productName != null && _name.text.isEmpty) _name.text = draft.productName!;
      if (draft.brand != null && _brand.text.isEmpty) _brand.text = draft.brand!;
      if (draft.model != null && _model.text.isEmpty) _model.text = draft.model!;
      if (draft.seller != null && _seller.text.isEmpty) _seller.text = draft.seller!;
      if (draft.price != null && _price.text.isEmpty) {
        _price.text = draft.price!.replaceAll(RegExp(r'[^0-9.]'), '');
      }
    });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(
            'Extracted a draft${count > 1 ? ' from $count images' : ''} '
            '(confidence ${(draft.confidence * 100).toStringAsFixed(0)}%). '
            'Please review every field before saving.'),
        backgroundColor: OwnlyTheme.success,
      ));
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _saving = true; _error = null; });
    try {
      await ref.read(repositoryProvider).createProduct({
        'name': _name.text.trim(),
        'brand': _brand.text.trim().isEmpty ? null : _brand.text.trim(),
        'model_number': _model.text.trim().isEmpty ? null : _model.text.trim(),
        'category': _category,
        'purchase_date': _purchaseDate.toIso8601String(),
        'purchase_price':
            _price.text.trim().isEmpty ? null : double.tryParse(_price.text.trim()),
        'currency': 'USD',
        'seller': _seller.text.trim().isEmpty ? null : _seller.text.trim(),
        'serial_number': _serial.text.trim().isEmpty ? null : _serial.text.trim(),
        'return_days': _returnDays,
      });
      if (_warrantyMonths != null) {
        final products = await ref.read(repositoryProvider).products(search: _name.text.trim());
        if (products.isNotEmpty) {
          await ref.read(repositoryProvider).addWarranty(products.first.id, {
            'warranty_type': 'manufacturer',
            'start_date': _purchaseDate.toIso8601String(),
            'duration_months': _warrantyMonths,
          });
        }
      }
      ref.read(productsProvider.notifier).refresh();
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() { _saving = false; _error = e.message; });
    } catch (e) {
      setState(() { _saving = false; _error = 'Could not save: $e'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add product')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      const Icon(Icons.document_scanner_outlined, color: OwnlyTheme.seed),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Text('Scan receipt or invoice',
                            style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                      FilledButton.tonal(
                        onPressed: _ocrRunning ? null : _scanReceipt,
                        child: _ocrRunning
                            ? const SizedBox(height: 18, width: 18,
                                child: CircularProgressIndicator(strokeWidth: 2))
                            : const Text('Camera'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: _ocrRunning ? null : _pickFromGallery,
                        child: const Text('Gallery'),
                      ),
                    ]),
                    if (_draft != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        'Draft extracted · confidence ${(_draft!.confidence * 100).toStringAsFixed(0)}%. '
                        'Review and edit the fields below — nothing is saved automatically.',
                        style: const TextStyle(fontSize: 12, color: OwnlyTheme.success),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Product name *'),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Product name is required' : null,
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _brand,
              decoration: const InputDecoration(labelText: 'Brand'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _model,
              decoration: const InputDecoration(labelText: 'Model number'),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<String>(
              initialValue: _category,
              decoration: const InputDecoration(labelText: 'Category'),
              items: [
                for (final c in categories)
                  DropdownMenuItem(value: c.id, child: Row(children: [
                    Icon(c.icon, size: 18), const SizedBox(width: 8), Text(c.label),
                  ])),
              ],
              onChanged: (v) => setState(() => _category = v ?? 'other'),
            ),
            const SizedBox(height: 14),
            InkWell(
              onTap: _pickDate,
              borderRadius: BorderRadius.circular(12),
              child: InputDecorator(
                decoration: const InputDecoration(labelText: 'Purchase date *'),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(MaterialLocalizations.of(context).formatFullDate(_purchaseDate)),
                    const Icon(Icons.calendar_today, size: 18),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _price,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Purchase price'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _seller,
              decoration: const InputDecoration(labelText: 'Seller / store'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _serial,
              decoration: const InputDecoration(labelText: 'Serial number'),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<int>(
              initialValue: _returnDays,
              decoration: const InputDecoration(labelText: 'Return window'),
              items: const [
                DropdownMenuItem(value: 0, child: Text('Not tracked')),
                DropdownMenuItem(value: 7, child: Text('7 days')),
                DropdownMenuItem(value: 14, child: Text('14 days')),
                DropdownMenuItem(value: 30, child: Text('30 days')),
                DropdownMenuItem(value: 90, child: Text('90 days')),
              ],
              onChanged: (v) => setState(() => _returnDays = v ?? 0),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<int>(
              initialValue: _warrantyMonths,
              decoration: const InputDecoration(labelText: 'Warranty duration'),
              items: const [
                DropdownMenuItem(value: 6, child: Text('6 months')),
                DropdownMenuItem(value: 12, child: Text('1 year')),
                DropdownMenuItem(value: 24, child: Text('2 years')),
                DropdownMenuItem(value: 36, child: Text('3 years')),
              ],
              onChanged: (v) => setState(() => _warrantyMonths = v),
              hint: const Text('No warranty'),
            ),
            const SizedBox(height: 20),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!, style: const TextStyle(color: OwnlyTheme.danger)),
              ),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(height: 22, width: 22,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Save product'),
            ),
          ],
        ),
      ),
    );
  }
}