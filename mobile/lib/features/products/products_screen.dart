import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/constants/categories.dart';
import 'package:ownly/core/theme/ownly_theme.dart';
import 'package:ownly/core/utils/formatters.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/features/products/product_detail_screen.dart';
import 'package:ownly/features/products/products_controller.dart';

/// Product Vault: searchable, filterable list of everything the user owns.
class ProductsScreen extends ConsumerStatefulWidget {
  const ProductsScreen({super.key});

  @override
  ConsumerState<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends ConsumerState<ProductsScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilter(ProductsFilter filter) {
    ref.read(productsFilterProvider.notifier).state = filter;
    ref.read(productsProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final products = ref.watch(productsProvider);
    final filter = ref.watch(productsFilterProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Products')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search name, brand, model…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _applyFilter(filter.copyWith(search: ''));
                        },
                      )
                    : null,
              ),
              onSubmitted: (q) => _applyFilter(filter.copyWith(search: q)),
            ),
          ),
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              children: [
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: const Text('All'),
                    selected: filter.warrantyStatus.isEmpty,
                    onSelected: (_) => _applyFilter(filter.copyWith(warrantyStatus: '')),
                    selectedColor: OwnlyTheme.seed.withValues(alpha: 0.15),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: const Text('Expiring'),
                    selected: filter.warrantyStatus == 'expiring',
                    onSelected: (_) => _applyFilter(filter.copyWith(warrantyStatus: 'expiring')),
                    selectedColor: OwnlyTheme.warning.withValues(alpha: 0.2),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: products.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text('$e', textAlign: TextAlign.center,
                      style: const TextStyle(color: OwnlyTheme.muted)),
                ),
              ),
              data: (items) => items.isEmpty
                  ? const Center(
                      child: Text('No products yet.\nTap Add to create your first one.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: OwnlyTheme.muted)))
                  : RefreshIndicator(
                      onRefresh: () => ref.read(productsProvider.notifier).refresh(),
                      child: ListView.builder(
                        itemCount: items.length,
                        itemBuilder: (context, i) => _ProductCard(
                          product: items[i],
                          onTap: () async {
                            await Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => ProductDetailScreen(productId: items[i].id),
                            ));
                            if (mounted) ref.read(productsProvider.notifier).refresh();
                          },
                        ),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  final Product product;
  final VoidCallback onTap;
  const _ProductCard({required this.product, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        onTap: onTap,
        leading: CircleAvatar(
          backgroundColor: OwnlyTheme.seed.withValues(alpha: 0.1),
          child: Icon(categoryIcon(product.category), color: OwnlyTheme.seed, size: 20),
        ),
        title: Text(product.name,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          'Purchased ${Formatters.shortDate(product.purchaseDate)}'
          '${product.purchasePrice != null ? ' · ${Formatters.money(product.purchasePrice, product.currency)}' : ''}',
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(statusLabel(product.warranty.status),
                style: TextStyle(
                  fontSize: 12, fontWeight: FontWeight.w700,
                  color: statusColor(product.warranty.status),
                )),
            if (product.warranty.daysRemaining != null &&
                product.warranty.status == 'expiring_soon')
              Text('${product.warranty.daysRemaining}d left',
                  style: const TextStyle(fontSize: 11, color: OwnlyTheme.muted)),
          ],
        ),
      ),
    );
  }
}