import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ownly/core/network/api_client.dart';
import 'package:ownly/data/models.dart';
import 'package:ownly/data/repositories.dart';
import 'package:ownly/features/claims/claim_dossier_modal.dart';
import 'package:ownly/features/claims/claims_screen.dart';

class _FakeClaimRepository extends ClaimRepository {
  final List<WarrantyClaimItem> claims;

  _FakeClaimRepository({
    required this.claims,
  }) : super(ApiClient(Dio()));

  @override
  Future<List<WarrantyClaimItem>> listClaims({String? status, int limit = 50, int offset = 0}) async {
    if (status != null) {
      return claims.where((c) => c.status.toLowerCase() == status.toLowerCase()).toList();
    }
    return claims;
  }

  @override
  Future<List<WarrantyClaimItem>> listProductClaims(String productId) async {
    return claims.where((c) => c.productId == productId).toList();
  }

  @override
  Future<WarrantyClaimItem> getClaim(String claimId) async {
    final c = claims.firstWhere((element) => element.id == claimId, orElse: () => throw Exception('Not found'));
    return c;
  }

  @override
  Future<ClaimDossierItem> getClaimDossier(String claimId) async {
    throw UnimplementedError();
  }

  @override
  Future<BrandSupportItem> getBrandSupport(String brand) async {
    throw UnimplementedError();
  }
}

void main() {
  group('Phase 9: Warranty Claim Models JSON Deserialization', () {
    test('BrandSupportItem deserializes correctly', () {
      final json = {
        'brand': 'Apple',
        'category': 'Electronics',
        'support_phone': '1-800-275-2273',
        'support_url': 'https://support.apple.com',
        'claim_portal_url': 'https://getsupport.apple.com',
        'warranty_check_url': 'https://checkcoverage.apple.com',
        'serial_lookup_url': 'https://checkcoverage.apple.com',
        'support_hours': '24/7 Phone & Chat',
        'notes': 'AppleCare covers hardware.',
      };

      final item = BrandSupportItem.fromJson(json);
      expect(item.brand, 'Apple');
      expect(item.category, 'Electronics');
      expect(item.supportPhone, '1-800-275-2273');
      expect(item.claimPortalUrl, 'https://getsupport.apple.com');
      expect(item.warrantyCheckUrl, 'https://checkcoverage.apple.com');
      expect(item.supportHours, '24/7 Phone & Chat');
      expect(item.notes, 'AppleCare covers hardware.');
    });

    test('WarrantyClaimItem deserializes correctly with brand support', () {
      final json = {
        'id': 'claim-123',
        'product_id': 'prod-456',
        'product_name': 'MacBook Pro 16',
        'product_brand': 'Apple',
        'product_serial': 'C02G1234MD6R',
        'warranty_id': 'warr-789',
        'warranty_provider': 'AppleCare',
        'claim_reference': 'APP-RMA-9042',
        'title': 'Display Backlight Defect',
        'issue_description': 'Flickering horizontal lines on wake.',
        'status': 'in_review',
        'incident_date': '2026-09-20T14:30:00Z',
        'resolution_notes': 'Under review by authorized service technician.',
        'claim_cost_covered': 499.50,
        'contact_email': 'user@ownly.com',
        'contact_phone': '+1 555-0199',
        'created_at': '2026-09-21T10:00:00Z',
        'updated_at': '2026-09-22T11:00:00Z',
        'brand_support': {
          'brand': 'Apple',
          'category': 'Electronics',
          'support_phone': '1-800-275-2273',
          'support_url': 'https://support.apple.com',
          'claim_portal_url': 'https://getsupport.apple.com',
          'support_hours': '24/7 Phone',
        },
      };

      final claim = WarrantyClaimItem.fromJson(json);
      expect(claim.id, 'claim-123');
      expect(claim.productName, 'MacBook Pro 16');
      expect(claim.productBrand, 'Apple');
      expect(claim.productSerial, 'C02G1234MD6R');
      expect(claim.claimReference, 'APP-RMA-9042');
      expect(claim.title, 'Display Backlight Defect');
      expect(claim.status, 'in_review');
      expect(claim.claimCostCovered, 499.50);
      expect(claim.brandSupport, isNotNull);
      expect(claim.brandSupport!.brand, 'Apple');
      expect(claim.brandSupport!.supportPhone, '1-800-275-2273');
    });

    test('ClaimDossierItem deserializes correctly', () {
      final json = {
        'dossier_id': 'dossier-001',
        'generated_at': '2026-09-24T12:00:00Z',
        'claim': {
          'id': 'claim-123',
          'product_id': 'prod-456',
          'product_name': 'MacBook Pro',
          'title': 'Keyboard Defect',
          'issue_description': 'Sticky spacebar',
          'status': 'submitted',
          'incident_date': '2026-09-20T00:00:00Z',
          'created_at': '2026-09-20T01:00:00Z',
          'updated_at': '2026-09-20T01:00:00Z',
        },
        'product': {
          'name': 'MacBook Pro',
          'brand': 'Apple',
          'serial_number': 'C02G9999',
        },
        'warranty': {
          'provider': 'AppleCare',
          'type': 'manufacturer',
          'status': 'active',
        },
        'documents': [
          {'name': 'Apple Store Receipt', 'type': 'invoice', 'download_url': 'https://s3.signed/doc.pdf'}
        ],
        'repairs': [],
        'claimant': {'name': 'John Doe', 'email': 'john@test.com'},
        'formatted_markdown': '# WARRANTY CLAIM DOSSIER\nProduct: MacBook Pro',
      };

      final dossier = ClaimDossierItem.fromJson(json);
      expect(dossier.dossierId, 'dossier-001');
      expect(dossier.claim.title, 'Keyboard Defect');
      expect(dossier.product['serial_number'], 'C02G9999');
      expect(dossier.documents.length, 1);
      expect(dossier.documents[0]['name'], 'Apple Store Receipt');
      expect(dossier.formattedMarkdown, contains('# WARRANTY CLAIM DOSSIER'));
    });
  });

  group('Phase 9: ClaimsScreen Widget Tests', () {
    testWidgets('Renders empty state when user has no claims', (tester) async {
      final fakeRepo = _FakeClaimRepository(claims: []);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            claimRepositoryProvider.overrideWithValue(fakeRepo),
          ],
          child: const MaterialApp(
            home: ClaimsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Warranty Claims'), findsOneWidget);
      expect(find.text('No Warranty Claims Found'), findsOneWidget);
      expect(find.text('All Claims'), findsOneWidget);
      expect(find.text('Draft'), findsOneWidget);
    });

    testWidgets('Renders claim card when claims exist', (tester) async {
      final sampleClaim = WarrantyClaimItem(
        id: 'claim-001',
        productId: 'prod-001',
        productName: 'Sony Headphones',
        productBrand: 'Sony',
        claimReference: 'SONY-CASE-4910',
        title: 'ANC Hiss in Right Ear',
        issueDescription: 'High pitch hiss sound',
        status: 'approved',
        incidentDate: DateTime(2026, 9, 18),
        claimCostCovered: 399.99,
        createdAt: DateTime(2026, 9, 18, 10),
        updatedAt: DateTime(2026, 9, 18, 12),
      );

      final fakeRepo = _FakeClaimRepository(claims: [sampleClaim]);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            claimRepositoryProvider.overrideWithValue(fakeRepo),
          ],
          child: const MaterialApp(
            home: ClaimsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('ANC Hiss in Right Ear'), findsOneWidget);
      expect(find.text('Product: Sony Headphones'), findsOneWidget);
      expect(find.text('APPROVED'), findsOneWidget);
      expect(find.text('Ref: SONY-CASE-4910'), findsOneWidget);
    });

    testWidgets('ClaimDossierModal renders sections and copy action', (tester) async {
      final sampleClaim = WarrantyClaimItem(
        id: 'c1',
        productId: 'p1',
        productName: 'Dell XPS 15',
        title: 'Battery Expansion',
        issueDescription: 'Trackpad displaced due to battery',
        status: 'approved',
        incidentDate: DateTime(2026, 9, 20),
        createdAt: DateTime(2026, 9, 20),
        updatedAt: DateTime(2026, 9, 20),
      );

      final dossier = ClaimDossierItem(
        dossierId: 'd1',
        generatedAt: DateTime(2026, 9, 24),
        claim: sampleClaim,
        product: {
          'name': 'Dell XPS 15',
          'brand': 'Dell',
          'model_number': '9520',
          'serial_number': 'DELL-TAG-8921',
          'purchase_date': '2026-01-15',
          'purchase_price': 1899.0,
        },
        warranty: {
          'provider': 'Dell ProSupport',
          'type': 'extended',
          'end_date': '2027-01-15',
          'status': 'active',
        },
        documents: [
          {'name': 'Invoice_Dell.pdf', 'type': 'invoice', 'download_url': 'https://download'}
        ],
        claimant: {'name': 'Alice Smith', 'email': 'alice@ownly.com'},
        formattedMarkdown: '# WARRANTY CLAIM DOSSIER\nDell XPS 15',
      );

      await tester.binding.setSurfaceSize(const Size(1080, 1920));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ClaimDossierModal(dossier: dossier),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Warranty Claim Dossier'), findsOneWidget);
      expect(find.text('Dell XPS 15'), findsOneWidget);
      expect(find.text('DELL-TAG-8921'), findsOneWidget);
      expect(find.text('Battery Expansion'), findsOneWidget);
      expect(find.text('Invoice_Dell.pdf'), findsOneWidget);
      expect(find.text('Copy Formatted Claim Dossier Markdown'), findsOneWidget);
    });
  });
}
