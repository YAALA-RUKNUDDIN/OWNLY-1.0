import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/products/products_controller.dart';

/// Repairs tab: repair history + add-repair form
/// (GET/POST /products/{id}/repairs). Saving also refreshes the product
/// timeline, where each repair appears as a `repair_recorded` event.
class RepairsTab extends ConsumerStatefulWidget {
  final String productId;
  final String currency;
  const RepairsTab({super.key, required this.productId, this.currency = 'USD'});

  @override
  ConsumerState<RepairsTab> createState() => _RepairsTabState();
}

class _RepairsTabState extends ConsumerState<RepairsTab> {
  late Future<List<RepairEntry>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(repositoryProvider).repairs(widget.productId);
  }

  void _reload() {
    setState(() =>
        _future = ref.read(repositoryProvider).repairs(widget.productId));
  }

  Future<void> _addRepair() async {
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const _RepairDialog(),
    );
    if (body == null) return;
    try {
      await ref.read(repositoryProvider).addRepair(widget.productId, body);
      _reload();
      // Repairs show up on the timeline too — refresh the detail screen.
      ref.read(productDetailProvider(widget.productId).notifier).load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not save repair: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        FutureBuilder<List<RepairEntry>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Could not load repairs: ${snap.error}',
                          textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      FilledButton.tonal(
                          onPressed: _reload, child: const Text('Retry')),
                    ],
                  ),
                ),
              );
            }
            final repairs = snap.data ?? const <RepairEntry>[];
            if (repairs.isEmpty) {
              return const Center(
                child: Text(
                    'No repairs yet.\nLog a repair to keep history here.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: OwnlyTheme.muted)),
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 84),
              itemCount: repairs.length,
              itemBuilder: (context, i) {
                final repair = repairs[i];
                final subtitle = [
                  Formatters.date(repair.repairDate),
                  if (repair.provider != null && repair.provider!.isNotEmpty)
                    repair.provider!,
                ].join(' · ');
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.build_outlined,
                        color: OwnlyTheme.seed),
                    title: Text(repair.description),
                    subtitle: Text(subtitle),
                    trailing: Text(
                      Formatters.money(repair.cost, widget.currency),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                );
              },
            );
          },
        ),
        Positioned(
          right: 16,
          bottom: 16,
          child: FloatingActionButton.extended(
            onPressed: _addRepair,
            icon: const Icon(Icons.add),
            label: const Text('Add repair'),
          ),
        ),
      ],
    );
  }
}

/// Add-repair dialog: date, description (required), provider, cost, notes.
class _RepairDialog extends StatefulWidget {
  const _RepairDialog();

  @override
  State<_RepairDialog> createState() => _RepairDialogState();
}

class _RepairDialogState extends State<_RepairDialog> {
  final _formKey = GlobalKey<FormState>();
  final _description = TextEditingController();
  final _provider = TextEditingController();
  final _cost = TextEditingController();
  final _notes = TextEditingController();
  DateTime _date = DateTime.now();

  @override
  void dispose() {
    _description.dispose();
    _provider.dispose();
    _cost.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(1990),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop({
      'repair_date': '${_date.year.toString().padLeft(4, '0')}-'
          '${_date.month.toString().padLeft(2, '0')}-'
          '${_date.day.toString().padLeft(2, '0')}',
      'description': _description.text.trim(),
      'provider': _provider.text.trim().isEmpty ? null : _provider.text.trim(),
      'cost':
          _cost.text.trim().isEmpty ? null : double.tryParse(_cost.text.trim()),
      'notes': _notes.text.trim().isEmpty ? null : _notes.text.trim(),
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add repair'),
      content: SizedBox(
        width: double.maxFinite,
        child: Form(
          key: _formKey,
          child: ListView(
            shrinkWrap: true,
            children: [
              InkWell(
                onTap: _pickDate,
                borderRadius: BorderRadius.circular(12),
                child: InputDecorator(
                  decoration: const InputDecoration(labelText: 'Repair date *'),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(MaterialLocalizations.of(context)
                          .formatFullDate(_date)),
                      const Icon(Icons.calendar_today, size: 18),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _description,
                decoration: const InputDecoration(labelText: 'Description *'),
                validator: (v) => (v == null || v.trim().isEmpty)
                    ? 'Description is required'
                    : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _provider,
                decoration:
                    const InputDecoration(labelText: 'Provider / shop'),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _cost,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Cost'),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  final cost = double.tryParse(v.trim());
                  if (cost == null || cost < 0) return 'Enter a valid cost';
                  return null;
                },
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _notes,
                decoration: const InputDecoration(labelText: 'Notes'),
                maxLines: 3,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel')),
        FilledButton(onPressed: _save, child: const Text('Save repair')),
      ],
    );
  }
}