import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/products/resale_tab.dart';
import 'package:ownly/features/resale/portfolio_analytics_screen.dart';
import 'package:ownly/features/resale/resale_listing_modal.dart';

class _FakeResaleRepository extends ResaleRepository {
  final ProductValuationItem? valuation;
  final PortfolioAnalyticsItem? analytics;

  _FakeResaleRepository({
    this.valuation,
    this.analytics,
  }) : super(ApiClient(Dio()));

  @override
  Future<ProductValuationItem> getValuation(String productId) async {
    if (valuation != null) return valuation!;
    throw Exception('Valuation not found');
  }

  @override
  Future<ResaleListingPacketItem> getResalePacket(String productId) async {
    throw UnimplementedError();
  }

  @override
  Future<PortfolioAnalyticsItem> getPortfolioAnalytics() async {
    if (analytics != null) return analytics!;
    throw Exception('Analytics not found');
  }

  @override
  Future<ProductValuationItem> updateCondition(String productId, String condition) async {
    if (valuation != null) return valuation!;
    throw Exception('Failed to update condition');
  }

  @override
  Future<ProductValuationItem> sellProduct(
    String productId, {
    required double resalePrice,
    DateTime? resaleDate,
    String? resalePlatform,
    String? resaleNotes,
    String? condition,
  }) async {
    if (valuation != null) return valuation!;
    throw Exception('Failed to mark sold');
  }

  @override
  Future<ProductValuationItem> disposeProduct(
    String productId, {
    required String disposalType,
    DateTime? disposalDate,
    String? notes,
  }) async {
    if (valuation != null) return valuation!;
    throw Exception('Failed to mark disposed');
  }
}

void main() {
  group('Phase 10: Resale Models JSON Deserialization', () {
    test('PriceRangeItem deserializes correctly', () {
      final json = {'low': 450.0, 'fair': 520.0, 'high': 600.0};
      final item = PriceRangeItem.fromJson(json);
      expect(item.low, 450.0);
      expect(item.fair, 520.0);
      expect(item.high, 600.0);
    });

    test('ProductValuationItem deserializes correctly', () {
      final json = {
        'product_id': 'prod-001',
        'product_name': 'iPhone 15 Pro',
        'brand': 'Apple',
        'category': 'electronics',
        'condition': 'mint',
        'purchase_date': '2025-10-01T00:00:00Z',
        'purchase_price': 999.0,
        'currency': 'USD',
        'days_owned': 358,
        'estimated_resale_value': 750.0,
        'value_retention_percent': 75.1,
        'total_repairs_cost': 49.0,
        'net_cost_of_ownership': 298.0,
        'cost_per_day': 0.83,
        'depreciation_amount': 249.0,
        'annual_depreciation_rate': 0.25,
        'suggested_listing_price_range': {'low': 700.0, 'fair': 750.0, 'high': 800.0},
        'is_sold': false,
        'actual_resale_price': null,
        'realized_net_cost': null,
      };

      final val = ProductValuationItem.fromJson(json);
      expect(val.productId, 'prod-001');
      expect(val.productName, 'iPhone 15 Pro');
      expect(val.brand, 'Apple');
      expect(val.condition, 'mint');
      expect(val.purchasePrice, 999.0);
      expect(val.estimatedResaleValue, 750.0);
      expect(val.valueRetentionPercent, 75.1);
      expect(val.totalRepairsCost, 49.0);
      expect(val.netCostOfOwnership, 298.0);
      expect(val.costPerDay, 0.83);
      expect(val.isSold, false);
      expect(val.suggestedListingPriceRange, isNotNull);
      expect(val.suggestedListingPriceRange!.fair, 750.0);
    });

    test('ResaleListingPacketItem deserializes correctly', () {
      final json = {
        'product_id': 'prod-001',
        'title': 'Apple iPhone 15 Pro (Mint Condition) - Verified Ownership',
        'suggested_price': 750.0,
        'suggested_price_range': {'low': 700.0, 'fair': 750.0, 'high': 800.0},
        'condition': 'mint',
        'specifications': {'brand': 'Apple', 'model': 'iPhone 15 Pro', 'category': 'electronics'},
        'repair_history': [
          {
            'repair_date': '2026-03-01',
            'repair_vendor': 'Apple Genius Bar',
            'description': 'Battery replacement',
            'cost': 49.0,
          }
        ],
        'verified_documents': [
          {'name': 'Apple Invoice', 'type': 'invoice', 'download_url': 'https://download/invoice.pdf'}
        ],
        'formatted_markdown': '# Apple iPhone 15 Pro\nCondition: Mint',
        'plain_text_description': 'Apple iPhone 15 Pro in Mint condition.',
      };

      final packet = ResaleListingPacketItem.fromJson(json);
      expect(packet.productId, 'prod-001');
      expect(packet.title, contains('Apple iPhone 15 Pro'));
      expect(packet.suggestedPrice, 750.0);
      expect(packet.condition, 'mint');
      expect(packet.repairHistory.length, 1);
      expect(packet.repairHistory[0].repairVendor, 'Apple Genius Bar');
      expect(packet.verifiedDocuments.length, 1);
      expect(packet.verifiedDocuments[0].name, 'Apple Invoice');
      expect(packet.formattedMarkdown, contains('# Apple iPhone 15 Pro'));
    });

    test('PortfolioAnalyticsItem deserializes correctly', () {
      final json = {
        'total_products_count': 12,
        'active_products_count': 9,
        'sold_products_count': 2,
        'disposed_products_count': 1,
        'total_purchase_value': 4500.0,
        'total_estimated_resale_value': 3100.0,
        'total_realized_from_sales': 850.0,
        'total_net_cost_of_ownership': 1400.0,
        'average_value_retention_percent': 68.9,
        'categories_breakdown': [
          {
            'category': 'electronics',
            'product_count': 5,
            'total_purchase_value': 3000.0,
            'total_estimated_resale_value': 2100.0,
            'retention_percent': 70.0,
          }
        ],
      };

      final item = PortfolioAnalyticsItem.fromJson(json);
      expect(item.totalProductsCount, 12);
      expect(item.activeProductsCount, 9);
      expect(item.soldProductsCount, 2);
      expect(item.disposedProductsCount, 1);
      expect(item.totalPurchaseValue, 4500.0);
      expect(item.totalEstimatedResaleValue, 3100.0);
      expect(item.averageValueRetentionPercent, 68.9);
      expect(item.categoriesBreakdown.length, 1);
      expect(item.categoriesBreakdown[0].category, 'electronics');
    });
  });

  group('Phase 10: PortfolioAnalyticsScreen Widget Tests', () {
    testWidgets('Renders portfolio analytics metrics and breakdown', (tester) async {
      const sampleAnalytics = PortfolioAnalyticsItem(
        totalProductsCount: 8,
        activeProductsCount: 6,
        soldProductsCount: 1,
        disposedProductsCount: 1,
        totalPurchaseValue: 3500.0,
        totalEstimatedResaleValue: 2450.0,
        totalRealizedFromSales: 400.0,
        totalNetCostOfOwnership: 1050.0,
        averageValueRetentionPercent: 70.0,
        categoriesBreakdown: [
          CategoryValueBreakdownItem(
            category: 'electronics',
            productCount: 4,
            totalPurchaseValue: 2500.0,
            totalEstimatedResaleValue: 1800.0,
            retentionPercent: 72.0,
          ),
          CategoryValueBreakdownItem(
            category: 'appliances',
            productCount: 2,
            totalPurchaseValue: 1000.0,
            totalEstimatedResaleValue: 650.0,
            retentionPercent: 65.0,
          ),
        ],
      );

      final fakeRepo = _FakeResaleRepository(analytics: sampleAnalytics);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            resaleRepositoryProvider.overrideWithValue(fakeRepo),
          ],
          child: const MaterialApp(
            home: PortfolioAnalyticsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Portfolio & Resale Analytics'), findsOneWidget);
      expect(find.text('TOTAL ESTIMATED RESALE VALUE'), findsOneWidget);
      expect(find.text('\$2450.00 USD'), findsOneWidget);
      expect(find.text('70.0% RETAINED'), findsOneWidget);
      expect(find.text('Category Value Retention'), findsOneWidget);
      expect(find.text('ELECTRONICS'), findsOneWidget);
      expect(find.text('APPLIANCES'), findsOneWidget);
      expect(find.text('Active'), findsOneWidget);
      expect(find.text('Sold'), findsOneWidget);
    });
  });

  group('Phase 10: ResaleListingModal Widget Tests', () {
    testWidgets('Renders resale listing packet details', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      const samplePacket = ResaleListingPacketItem(
        productId: 'prod-123',
        title: 'Sony WH-1000XM5 Noise Canceling Headphones',
        suggestedPrice: 280.0,
        suggestedPriceRange: PriceRangeItem(low: 250.0, fair: 280.0, high: 310.0),
        condition: 'excellent',
        specifications: {'brand': 'Sony', 'category': 'electronics'},
        repairHistory: [
          ResaleRepairItem(
            repairDate: '2026-01-15',
            repairVendor: 'Sony Authorized Care',
            description: 'Ear pad replacement',
            cost: 35.0,
          )
        ],
        verifiedDocuments: [
          ResaleDocumentItem(
            name: 'Original Invoice',
            type: 'invoice',
            downloadUrl: 'https://cdn/doc.pdf',
          )
        ],
        formattedMarkdown: '# Sony WH-1000XM5\nPrice: \$280',
        plainTextDescription: 'Sony WH-1000XM5 in excellent condition.',
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ResaleListingModal(packet: samplePacket),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Marketplace Resale Listing'), findsOneWidget);
      expect(find.text('Sony WH-1000XM5 Noise Canceling Headphones'), findsOneWidget);
      expect(find.text('\$280.00 USD'), findsOneWidget);
      expect(find.text('EXCELLENT'), findsOneWidget);
      expect(find.text('Verified Repair & Maintenance History'), findsOneWidget);
      expect(find.text('Sony Authorized Care'), findsOneWidget);
      expect(find.text('Verified Purchase & Authenticity Proof'), findsOneWidget);
      expect(find.text('Original Invoice'), findsOneWidget);
      expect(find.text('Copy Markdown'), findsOneWidget);
    });
  });

  group('Phase 10: ResaleTab Widget Tests', () {
    testWidgets('Renders valuation card, condition chips, and actions', (tester) async {
      final sampleProduct = Product.fromJson({
        'id': 'prod-001',
        'name': 'Dell XPS 15',
        'category': 'electronics',
        'condition': 'good',
        'purchase_date': '2025-06-01T00:00:00Z',
        'purchase_price': 1800.0,
        'currency': 'USD',
        'status': 'active',
        'return_days': 30,
        'warranty': {'status': 'active', 'days_remaining': 120},
        'return_window': {'tracked': false, 'status': 'none'},
        'created_at': '2025-06-01T00:00:00Z',
      });

      final sampleValuation = ProductValuationItem(
        productId: 'prod-001',
        productName: 'Dell XPS 15',
        brand: 'Dell',
        category: 'electronics',
        condition: 'good',
        purchaseDate: DateTime(2025, 6, 1),
        purchasePrice: 1800.0,
        currency: 'USD',
        daysOwned: 480,
        estimatedResaleValue: 1100.0,
        valueRetentionPercent: 61.1,
        totalRepairsCost: 120.0,
        netCostOfOwnership: 820.0,
        costPerDay: 1.71,
        depreciationAmount: 700.0,
        annualDepreciationRate: 0.25,
        suggestedListingPriceRange: const PriceRangeItem(low: 1000.0, fair: 1100.0, high: 1200.0),
        isSold: false,
      );

      final fakeRepo = _FakeResaleRepository(valuation: sampleValuation);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            resaleRepositoryProvider.overrideWithValue(fakeRepo),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: ResaleTab(product: sampleProduct),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('ESTIMATED RESALE VALUE'), findsOneWidget);
      expect(find.text('\$1100.00 USD'), findsOneWidget);
      expect(find.text('61.1% RETAINED'), findsOneWidget);
      expect(find.text('Net Cost to Date'), findsOneWidget);
      expect(find.text('Product Condition & Quality'), findsOneWidget);
      expect(find.text('Generate Marketplace Resale Listing'), findsOneWidget);
      expect(find.text('Mark as Sold'), findsOneWidget);
      expect(find.text('Recycle / Donate'), findsOneWidget);
    });
  });
}
