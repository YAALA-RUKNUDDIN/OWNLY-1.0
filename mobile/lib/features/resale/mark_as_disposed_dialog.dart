import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class MarkAsDisposedDialog extends ConsumerStatefulWidget {
  final Product product;

  const MarkAsDisposedDialog({super.key, required this.product});

  @override
  ConsumerState<MarkAsDisposedDialog> createState() => _MarkAsDisposedDialogState();
}

class _MarkAsDisposedDialogState extends ConsumerState<MarkAsDisposedDialog> {
  String _disposalType = 'recycled';
  late final TextEditingController _notesCtrl;
  late DateTime _disposalDate;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _notesCtrl = TextEditingController();
    _disposalDate = DateTime.now();
  }

  @override
  void dispose() {
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await ref.read(resaleRepositoryProvider).disposeProduct(
            widget.product.id,
            disposalType: _disposalType,
            disposalDate: _disposalDate,
            notes: _notesCtrl.text.trim().isNotEmpty ? _notesCtrl.text.trim() : null,
          );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to record exit: $e')),
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
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.recycling, color: OwnlyColors.emerald, size: 24),
                  const SizedBox(width: 10),
                  const Text(
                    'Retire / Dispose Product',
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
                'Log responsible disposal, donation, or archiving for ${widget.product.name}.',
                style: const TextStyle(fontSize: 13, color: OwnlyColors.textSecondary),
              ),
              const SizedBox(height: 20),

              // Type selector
              DropdownButtonFormField<String>(
                initialValue: _disposalType,
                decoration: const InputDecoration(labelText: 'Exit Method'),
                items: const [
                  DropdownMenuItem(
                    value: 'recycled',
                    child: Text('Recycled (Certified E-Waste / Eco Center)'),
                  ),
                  DropdownMenuItem(
                    value: 'donated',
                    child: Text('Donated (Charity / Non-Profit / Gift)'),
                  ),
                  DropdownMenuItem(
                    value: 'archived',
                    child: Text('Archived (Broken / Retired to storage)'),
                  ),
                ],
                onChanged: (v) => setState(() => _disposalType = v ?? 'recycled'),
              ),
              const SizedBox(height: 16),

              // Notes field
              TextFormField(
                controller: _notesCtrl,
                decoration: const InputDecoration(
                  labelText: 'Facility / Donation Notes',
                  hintText: 'e.g. Goodwill receipt #1234 or Best Buy drop-off',
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 24),

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
                        : const Text('Confirm Exit'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
