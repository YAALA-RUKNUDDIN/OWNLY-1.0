import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/constants/categories.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class PortfolioAnalyticsScreen extends ConsumerStatefulWidget {
  const PortfolioAnalyticsScreen({super.key});

  @override
  ConsumerState<PortfolioAnalyticsScreen> createState() => _PortfolioAnalyticsScreenState();
}

class _PortfolioAnalyticsScreenState extends ConsumerState<PortfolioAnalyticsScreen> {
  late Future<PortfolioAnalyticsItem> _analyticsFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _analyticsFuture = ref.read(resaleRepositoryProvider).getPortfolioAnalytics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Portfolio & Resale Analytics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => setState(() => _load()),
          ),
        ],
      ),
      body: FutureBuilder<PortfolioAnalyticsItem>(
        future: _analyticsFuture,
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
                    Text('Failed to load portfolio analytics: ${snapshot.error}', textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    ElevatedButton(onPressed: () => setState(() => _load()), child: const Text('Retry')),
                  ],
                ),
              ),
            );
          }

          final data = snapshot.data!;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Hero Summary Card
              Container(
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
                          'TOTAL ESTIMATED RESALE VALUE',
                          style: TextStyle(
                            fontSize: 11,
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
                            '${data.averageValueRetentionPercent.toStringAsFixed(1)}% RETAINED',
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
                      '\$${data.totalEstimatedResaleValue.toStringAsFixed(2)} USD',
                      style: const TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w900,
                        color: OwnlyColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Original Portfolio Purchase Cost: \$${data.totalPurchaseValue.toStringAsFixed(2)} USD',
                      style: const TextStyle(fontSize: 12, color: OwnlyColors.textSecondary),
                    ),
                    const Divider(height: 24, color: OwnlyColors.border),
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetricTile(
                            'Realized Sales',
                            '\$${data.totalRealizedFromSales.toStringAsFixed(2)}',
                          ),
                        ),
                        Expanded(
                          child: _buildMetricTile(
                            'Total Net Cost',
                            '\$${data.totalNetCostOfOwnership.toStringAsFixed(2)}',
                          ),
                        ),
                        Expanded(
                          child: _buildMetricTile(
                            'Products',
                            '${data.totalProductsCount} items',
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Status Counts Chips
              Row(
                children: [
                  _buildCountChip('Active', data.activeProductsCount, OwnlyColors.emerald),
                  const SizedBox(width: 8),
                  _buildCountChip('Sold', data.soldProductsCount, Colors.amber.shade700),
                  const SizedBox(width: 8),
                  _buildCountChip('Disposed / Retired', data.disposedProductsCount, OwnlyColors.textSecondary),
                ],
              ),
              const SizedBox(height: 24),

              // Category Breakdown List
              const Text(
                'Category Value Retention',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: OwnlyColors.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              if (data.categoriesBreakdown.isEmpty)
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: OwnlyColors.card,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: OwnlyColors.border),
                  ),
                  child: const Center(
                    child: Text(
                      'No products with recorded values yet.',
                      style: TextStyle(color: OwnlyColors.textSecondary),
                    ),
                  ),
                )
              else
                ...data.categoriesBreakdown.map((cat) => Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: OwnlyColors.card,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: OwnlyColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 16,
                                backgroundColor: OwnlyColors.emerald.withValues(alpha: 0.12),
                                child: Icon(categoryIcon(cat.category), size: 16, color: OwnlyColors.emerald),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      cat.category.replaceAll('_', ' ').toUpperCase(),
                                      style: const TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                        color: OwnlyColors.textPrimary,
                                      ),
                                    ),
                                    Text(
                                      '${cat.productCount} ${cat.productCount == 1 ? 'item' : 'items'}',
                                      style: const TextStyle(fontSize: 11, color: OwnlyColors.textSecondary),
                                    ),
                                  ],
                                ),
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    '\$${cat.totalEstimatedResaleValue.toStringAsFixed(2)}',
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: OwnlyColors.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    '${cat.retentionPercent.toStringAsFixed(1)}% retained',
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: OwnlyColors.emerald,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: (cat.retentionPercent / 100.0).clamp(0.0, 1.0),
                              backgroundColor: OwnlyColors.border,
                              color: OwnlyColors.emerald,
                              minHeight: 6,
                            ),
                          ),
                        ],
                      ),
                    )),
            ],
          );
        },
      ),
    );
  }

  Widget _buildCountChip(String label, int count, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: OwnlyColors.card,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: OwnlyColors.border),
        ),
        child: Column(
          children: [
            Text(
              count.toString(),
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: const TextStyle(fontSize: 11, color: OwnlyColors.textSecondary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
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
}
