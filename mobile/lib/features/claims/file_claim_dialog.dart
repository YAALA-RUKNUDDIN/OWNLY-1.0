import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

/// Modal bottom sheet / dialog to file a warranty claim.
class FileClaimDialog extends ConsumerStatefulWidget {
  final Product product;
  final String? warrantyId;

  const FileClaimDialog({
    super.key,
    required this.product,
    this.warrantyId,
  });

  static Future<WarrantyClaimItem?> show(
    BuildContext context, {
    required Product product,
    String? warrantyId,
  }) {
    return showModalBottomSheet<WarrantyClaimItem>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: FileClaimDialog(product: product, warrantyId: warrantyId),
      ),
    );
  }

  @override
  ConsumerState<FileClaimDialog> createState() => _FileClaimDialogState();
}

class _FileClaimDialogState extends ConsumerState<FileClaimDialog> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _referenceController = TextEditingController();
  final _phoneController = TextEditingController();

  DateTime _incidentDate = DateTime.now();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _referenceController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _incidentDate,
      firstDate: DateTime(2000),
      lastDate: now,
    );
    if (picked != null) {
      setState(() {
        _incidentDate = DateTime(
          picked.year,
          picked.month,
          picked.day,
          _incidentDate.hour,
          _incidentDate.minute,
        );
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final repo = ref.read(claimRepositoryProvider);
      final claim = await repo.createClaim(
        widget.product.id,
        title: _titleController.text.trim(),
        issueDescription: _descriptionController.text.trim(),
        incidentDate: _incidentDate,
        warrantyId: widget.warrantyId,
        claimReference: _referenceController.text.trim().isEmpty
            ? null
            : _referenceController.text.trim(),
        contactPhone: _phoneController.text.trim().isEmpty
            ? null
            : _phoneController.text.trim(),
      );
      if (mounted) {
        Navigator.of(context).pop(claim);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('MMM d, yyyy');

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: OwnlyTheme.seed.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.assignment_outlined, color: OwnlyTheme.seed),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'File Warranty Claim',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: OwnlyTheme.ink,
                          ),
                        ),
                        Text(
                          widget.product.name,
                          style: const TextStyle(fontSize: 13, color: OwnlyTheme.muted),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
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
              const SizedBox(height: 18),
              if (_error != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: OwnlyTheme.danger.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: OwnlyTheme.danger.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    _error!,
                    style: const TextStyle(fontSize: 13, color: OwnlyTheme.danger),
                  ),
                ),
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Issue Title *',
                  hintText: 'e.g. Screen flickering or Battery swelling',
                  prefixIcon: Icon(Icons.report_problem_outlined, size: 20),
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Please enter a brief issue title' : null,
              ),
              const SizedBox(height: 14),
              InkWell(
                onTap: _pickDate,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFFE1E5EE)),
                    borderRadius: BorderRadius.circular(12),
                    color: Colors.white,
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today_outlined, size: 20, color: OwnlyTheme.muted),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Incident Date', style: TextStyle(fontSize: 11, color: OwnlyTheme.muted)),
                          Text(
                            df.format(_incidentDate),
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: OwnlyTheme.ink),
                          ),
                        ],
                      ),
                      const Spacer(),
                      const Icon(Icons.arrow_drop_down, color: OwnlyTheme.muted),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _descriptionController,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Defect / Problem Description *',
                  hintText: 'Describe what happened, any error codes, or physical damage...',
                  alignLabelWithHint: true,
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Please describe the problem' : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _referenceController,
                decoration: const InputDecoration(
                  labelText: 'Claim / RMA Reference # (Optional)',
                  hintText: 'e.g. RMA-12345 or Support Case #',
                  prefixIcon: Icon(Icons.tag, size: 20),
                ),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'Contact Phone Number (Optional)',
                  hintText: 'e.g. +1 555-0199',
                  prefixIcon: Icon(Icons.phone_outlined, size: 20),
                ),
              ),
              const SizedBox(height: 22),
              ElevatedButton(
                onPressed: _submitting ? null : _submit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: OwnlyTheme.seed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  elevation: 0,
                ),
                child: _submitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text(
                        'File Claim & Generate Packet',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                      ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }
}
