import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';

class ProductsFilter {
  final String search;
  final String category;
  final String warrantyStatus;
  const ProductsFilter({this.search = '', this.category = '', this.warrantyStatus = ''});

  ProductsFilter copyWith({String? search, String? category, String? warrantyStatus}) =>
      ProductsFilter(
        search: search ?? this.search,
        category: category ?? this.category,
        warrantyStatus: warrantyStatus ?? this.warrantyStatus,
      );
}

class ProductsController extends StateNotifier<AsyncValue<List<Product>>> {
  final OwnlyRepository _repo;
  ProductsFilter _filter = const ProductsFilter();

  ProductsController(this._repo) : super(const AsyncValue.loading()) {
    refresh();
  }

  Future<void> refresh() async {
    try {
      final items = await _repo.products(
        search: _filter.search,
        category: _filter.category,
        warrantyStatus: _filter.warrantyStatus,
      );
      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void applyFilter(ProductsFilter filter) {
    _filter = filter;
    refresh();
  }
}

final productsFilterProvider = StateProvider<ProductsFilter>((ref) => const ProductsFilter());

final productsProvider = StateNotifierProvider<ProductsController, AsyncValue<List<Product>>>(
  (ref) => ProductsController(ref.watch(repositoryProvider)),
);

class ProductDetailState {
  final bool loading;
  final String? error;
  final Product? product;
  final List<TimelineEvent> timeline;
  final List<DocumentFile> documents;
  const ProductDetailState({
    this.loading = true,
    this.error,
    this.product,
    this.timeline = const [],
    this.documents = const [],
  });

  ProductDetailState copyWith({
    bool? loading, String? error, Product? product,
    List<TimelineEvent>? timeline, List<DocumentFile>? documents,
  }) =>
      ProductDetailState(
        loading: loading ?? this.loading,
        error: error,
        product: product ?? this.product,
        timeline: timeline ?? this.timeline,
        documents: documents ?? this.documents,
      );
}

class ProductDetailController extends StateNotifier<ProductDetailState> {
  final OwnlyRepository _repo;
  final String productId;

  ProductDetailController(this._repo, this.productId) : super(const ProductDetailState()) {
    load();
  }

  Future<void> load() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final product = await _repo.product(productId);
      final timeline = await _repo.timeline(productId);
      final documents = await _repo.documents(productId);
      state = ProductDetailState(
        loading: false, product: product, timeline: timeline, documents: documents,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<void> deleteProduct() async {
    await _repo.deleteProduct(productId);
  }
}

final productDetailProvider = StateNotifierProvider.family<ProductDetailController,
    ProductDetailState, String>(
  (ref, id) => ProductDetailController(ref.watch(repositoryProvider), id),
);