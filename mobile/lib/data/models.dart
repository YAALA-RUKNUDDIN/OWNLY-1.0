/// Plain data classes mirroring the OWNLY API responses.
class UserAccount {
  final String id;
  final String name;
  final String email;
  final bool isAdmin;
  UserAccount({required this.id, required this.name, required this.email, required this.isAdmin});

  factory UserAccount.fromJson(Map<String, dynamic> j) => UserAccount(
        id: j['id'] as String,
        name: j['name'] as String,
        email: j['email'] as String,
        isAdmin: (j['is_admin'] ?? false) as bool,
      );
}

class WarrantyInfo {
  final String status; // active | expiring_soon | expired | none
  final int? daysRemaining;
  final DateTime? endDate;
  WarrantyInfo({required this.status, this.daysRemaining, this.endDate});

  factory WarrantyInfo.fromJson(Map<String, dynamic> j) => WarrantyInfo(
        status: j['status'] as String,
        daysRemaining: j['days_remaining'] as int?,
        endDate: j['end_date'] != null ? DateTime.tryParse(j['end_date'] as String) : null,
      );
}

class ReturnWindow {
  final bool tracked;
  final String status;
  final int? daysRemaining;
  final DateTime? endDate;
  ReturnWindow({required this.tracked, required this.status, this.daysRemaining, this.endDate});

  factory ReturnWindow.fromJson(Map<String, dynamic> j) => ReturnWindow(
        tracked: (j['tracked'] ?? false) as bool,
        status: j['status'] as String,
        daysRemaining: j['days_remaining'] as int?,
        endDate: j['end_date'] != null ? DateTime.tryParse(j['end_date'] as String) : null,
      );
}

class Product {
  final String id;
  final String name;
  final String? brand;
  final String? modelNumber;
  final String category;
  final DateTime purchaseDate;
  final num? purchasePrice;
  final String currency;
  final String? seller;
  final String? serialNumber;
  final String status;
  final int returnDays;
  final WarrantyInfo warranty;
  final ReturnWindow returnWindow;
  final DateTime createdAt;
  final String? householdId;
  final bool isShared;

  Product({
    required this.id,
    required this.name,
    this.brand,
    this.modelNumber,
    required this.category,
    required this.purchaseDate,
    this.purchasePrice,
    required this.currency,
    this.seller,
    this.serialNumber,
    required this.status,
    required this.returnDays,
    required this.warranty,
    required this.returnWindow,
    required this.createdAt,
    this.householdId,
    this.isShared = false,
  });

  factory Product.fromJson(Map<String, dynamic> j) => Product(
        id: j['id'] as String,
        name: j['name'] as String,
        brand: j['brand'] as String?,
        modelNumber: j['model_number'] as String?,
        category: j['category'] as String,
        purchaseDate: DateTime.parse(j['purchase_date'] as String),
        purchasePrice: j['purchase_price'] as num?,
        currency: (j['currency'] ?? 'USD') as String,
        seller: j['seller'] as String?,
        serialNumber: j['serial_number'] as String?,
        status: j['status'] as String,
        returnDays: (j['return_days'] ?? 0) as int,
        warranty: WarrantyInfo.fromJson(j['warranty'] as Map<String, dynamic>),
        returnWindow: ReturnWindow.fromJson(j['return_window'] as Map<String, dynamic>),
        createdAt: DateTime.parse(j['created_at'] as String),
        householdId: j['household_id'] as String?,
        isShared: (j['is_shared'] ?? false) as bool,
      );
}

class AttentionItem {
  final String kind;
  final String severity;
  final String productId;
  final String productName;
  final String title;
  final String message;
  final DateTime dueDate;
  final int daysRemaining;

  AttentionItem({
    required this.kind,
    required this.severity,
    required this.productId,
    required this.productName,
    required this.title,
    required this.message,
    required this.dueDate,
    required this.daysRemaining,
  });

  factory AttentionItem.fromJson(Map<String, dynamic> j) => AttentionItem(
        kind: j['kind'] as String,
        severity: j['severity'] as String,
        productId: j['product_id'] as String,
        productName: (j['product_name'] ?? '') as String,
        title: j['title'] as String,
        message: j['message'] as String,
        dueDate: DateTime.parse(j['due_date'] as String),
        daysRemaining: j['days_remaining'] as int,
      );
}

class UpcomingItem {
  final String kind;
  final String? productId;
  final String? productName;
  final String title;
  final DateTime dueDate;
  final int daysRemaining;

  UpcomingItem({
    required this.kind,
    this.productId,
    this.productName,
    required this.title,
    required this.dueDate,
    required this.daysRemaining,
  });

  factory UpcomingItem.fromJson(Map<String, dynamic> j) => UpcomingItem(
        kind: j['kind'] as String,
        productId: j['product_id'] as String?,
        productName: j['product_name'] as String?,
        title: j['title'] as String,
        dueDate: DateTime.parse(j['due_date'] as String),
        daysRemaining: j['days_remaining'] as int,
      );
}

class DashboardStats {
  final int totalProducts;
  final int activeWarranties;
  final int expiringWarranties;
  final int documentsStored;
  DashboardStats({
    required this.totalProducts,
    required this.activeWarranties,
    required this.expiringWarranties,
    required this.documentsStored,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> j) => DashboardStats(
        totalProducts: j['total_products'] as int,
        activeWarranties: j['active_warranties'] as int,
        expiringWarranties: j['expiring_warranties'] as int,
        documentsStored: j['documents_stored'] as int,
      );
}

class TodayDashboard {
  final String greeting;
  final List<AttentionItem> attention;
  final List<UpcomingItem> upcoming;
  final List<Product> recentlyAdded;
  final DashboardStats stats;

  TodayDashboard({
    required this.greeting,
    required this.attention,
    required this.upcoming,
    required this.recentlyAdded,
    required this.stats,
  });

  factory TodayDashboard.fromJson(Map<String, dynamic> j) => TodayDashboard(
        greeting: j['greeting'] as String,
        attention: (j['attention'] as List).map((e) => AttentionItem.fromJson(e)).toList(),
        upcoming: (j['upcoming'] as List).map((e) => UpcomingItem.fromJson(e)).toList(),
        recentlyAdded: (j['recently_added'] as List).map((e) => Product.fromJson(e)).toList(),
        stats: DashboardStats.fromJson(j['stats'] as Map<String, dynamic>),
      );
}

/// One row of GET /users/me/prefs — a user's per-category notification
/// preference (warranty | return_window | service | custom).
class NotificationPref {
  final String category;
  final bool enabled;
  final List<int> leadDays;

  NotificationPref({
    required this.category,
    required this.enabled,
    required this.leadDays,
  });

  factory NotificationPref.fromJson(Map<String, dynamic> j) => NotificationPref(
        category: j['category'] as String,
        enabled: (j['enabled'] ?? true) as bool,
        leadDays: ((j['lead_days'] ?? const <dynamic>[]) as List).cast<int>(),
      );
}

class TimelineEvent {
  final String id;
  final String eventType;
  final String title;
  final String? description;
  final DateTime eventDate;
  TimelineEvent({
    required this.id,
    required this.eventType,
    required this.title,
    this.description,
    required this.eventDate,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> j) => TimelineEvent(
        id: j['id'] as String,
        eventType: j['event_type'] as String,
        title: j['title'] as String,
        description: j['description'] as String?,
        eventDate: DateTime.parse(j['event_date'] as String),
      );
}

class DocumentFile {
  final String id;
  final String productId;
  final String documentName;
  final String documentType;
  final int fileSize;
  final String mimeType;
  DocumentFile({
    required this.id,
    required this.productId,
    required this.documentName,
    required this.documentType,
    required this.fileSize,
    required this.mimeType,
  });

  factory DocumentFile.fromJson(Map<String, dynamic> j) => DocumentFile(
        id: j['id'] as String,
        productId: j['product_id'] as String,
        documentName: j['document_name'] as String,
        documentType: j['document_type'] as String,
        fileSize: j['file_size'] as int,
        mimeType: j['mime_type'] as String,
      );
}

class ReminderItem {
  final String id;
  final String? productId;
  final String title;
  final String? description;
  final String reminderType;
  final DateTime scheduledDate;
  final String status;
  ReminderItem({
    required this.id,
    this.productId,
    required this.title,
    this.description,
    required this.reminderType,
    required this.scheduledDate,
    required this.status,
  });

  factory ReminderItem.fromJson(Map<String, dynamic> j) => ReminderItem(
        id: j['id'] as String,
        productId: j['product_id'] as String?,
        title: j['title'] as String,
        description: j['description'] as String?,
        reminderType: j['reminder_type'] as String,
        scheduledDate: DateTime.parse(j['scheduled_date'] as String),
        status: j['status'] as String,
      );
}

class OcrDraft {
  final String? productName;
  final String? brand;
  final String? model;
  final String? purchaseDate;
  final String? price;
  final String? seller;
  final String? invoiceNumber;
  final double confidence;
  final String rawText;
  OcrDraft({
    this.productName,
    this.brand,
    this.model,
    this.purchaseDate,
    this.price,
    this.seller,
    this.invoiceNumber,
    required this.confidence,
    required this.rawText,
  });

  factory OcrDraft.fromJson(Map<String, dynamic> j) => OcrDraft(
        productName: j['product_name'] as String?,
        brand: j['brand'] as String?,
        model: j['model'] as String?,
        purchaseDate: j['purchase_date'] as String?,
        price: j['price'] as String?,
        seller: j['seller'] as String?,
        invoiceNumber: j['invoice_number'] as String?,
        confidence: (j['confidence'] as num?)?.toDouble() ?? 0,
        rawText: (j['raw_text'] ?? '') as String,
      );
}

/// GET /subscription — current plan, limits and usage.
/// Drives feature gating and upgrade prompts app-wide.
class SubscriptionInfo {
  final String tier; // free | premium
  final String status;
  final String provider;
  final DateTime? startedAt;
  final DateTime? expiresAt;
  final DateTime? canceledAt;
  final int? maxProducts; // null = unlimited
  final List<String> features;
  final int usedProducts;

  const SubscriptionInfo({
    this.tier = 'free',
    this.status = 'active',
    this.provider = 'free',
    this.startedAt,
    this.expiresAt,
    this.canceledAt,
    this.maxProducts,
    this.features = const [],
    this.usedProducts = 0,
  });

  bool get isPremium => tier == 'premium';

  factory SubscriptionInfo.fromJson(Map<String, dynamic> j) {
    final limits = (j['limits'] ?? const <String, dynamic>{}) as Map<String, dynamic>;
    final usage = (j['usage'] ?? const <String, dynamic>{}) as Map<String, dynamic>;
    return SubscriptionInfo(
      tier: (j['tier'] ?? 'free') as String,
      status: (j['status'] ?? '') as String,
      provider: (j['provider'] ?? '') as String,
      startedAt: DateTime.tryParse('${j['started_at']}'),
      expiresAt: DateTime.tryParse('${j['expires_at']}'),
      canceledAt: DateTime.tryParse('${j['canceled_at']}'),
      maxProducts: limits['max_products'] as int?,
      features: ((limits['features'] ?? const <dynamic>[]) as List).cast<String>(),
      usedProducts: (usage['products'] ?? 0) as int,
    );
  }
}

/// One row of GET /notifications — a logged notification (history entry).
class NotificationItem {
  final String id;
  final String category; // warranty | return_window | service | custom
  final String subjectType;
  final String subjectId;
  final String milestone;
  final DateTime? dueDate;
  final String title;
  final String body;
  final String deliveryStatus;
  final DateTime? sentAt;

  const NotificationItem({
    required this.id,
    required this.category,
    required this.subjectType,
    required this.subjectId,
    required this.milestone,
    this.dueDate,
    required this.title,
    required this.body,
    required this.deliveryStatus,
    this.sentAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> j) => NotificationItem(
        id: j['id'] as String,
        category: (j['category'] ?? '') as String,
        subjectType: (j['subject_type'] ?? '') as String,
        subjectId: (j['subject_id'] ?? '') as String,
        milestone: (j['milestone'] ?? '') as String,
        dueDate: DateTime.tryParse('${j['due_date']}'),
        title: (j['title'] ?? '') as String,
        body: (j['body'] ?? '') as String,
        deliveryStatus: (j['delivery_status'] ?? '') as String,
        sentAt: DateTime.tryParse('${j['sent_at']}'),
      );
}

/// Paginated envelope of GET /notifications (page_size default 20).
class NotificationPage {
  final List<NotificationItem> items;
  final int total;
  final int page;
  final int pageSize;

  const NotificationPage({
    required this.items,
    required this.total,
    this.page = 1,
    this.pageSize = 20,
  });

  factory NotificationPage.fromJson(Map<String, dynamic> j) => NotificationPage(
        items: ((j['items'] ?? const <dynamic>[]) as List)
            .cast<Map<String, dynamic>>()
            .map(NotificationItem.fromJson)
            .toList(),
        total: (j['total'] ?? 0) as int,
        page: (j['page'] ?? 1) as int,
        pageSize: (j['page_size'] ?? 20) as int,
      );
}

/// One row of GET /products/{id}/repairs — a repair in the product's history.
class RepairEntry {
  final String id;
  final String productId;
  final DateTime repairDate;
  final String description;
  final String? provider;
  final num? cost;
  final String? notes;

  const RepairEntry({
    required this.id,
    required this.productId,
    required this.repairDate,
    required this.description,
    this.provider,
    this.cost,
    this.notes,
  });

  factory RepairEntry.fromJson(Map<String, dynamic> j) => RepairEntry(
        id: j['id'] as String,
        productId: j['product_id'] as String,
        repairDate: DateTime.parse(j['repair_date'] as String),
        description: (j['description'] ?? '') as String,
        provider: j['provider'] as String?,
        cost: j['cost'] as num?,
        notes: j['notes'] as String?,
      );
}

/// Household summary in GET /households.
class HouseholdItem {
  final String id;
  final String name;
  final String createdBy;
  final int memberCount;
  final String role; // 'admin' | 'member' | 'viewer'
  final DateTime createdAt;

  const HouseholdItem({
    required this.id,
    required this.name,
    required this.createdBy,
    required this.memberCount,
    required this.role,
    required this.createdAt,
  });

  factory HouseholdItem.fromJson(Map<String, dynamic> j) => HouseholdItem(
        id: j['id'] as String,
        name: (j['name'] ?? '') as String,
        createdBy: j['created_by'] as String,
        memberCount: (j['member_count'] ?? 1) as int,
        role: (j['role'] ?? 'member') as String,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

/// Household member row in GET /households/{id}.
class HouseholdMemberItem {
  final String userId;
  final String userName;
  final String userEmail;
  final String role; // 'admin' | 'member' | 'viewer'
  final DateTime joinedAt;

  const HouseholdMemberItem({
    required this.userId,
    required this.userName,
    required this.userEmail,
    required this.role,
    required this.joinedAt,
  });

  factory HouseholdMemberItem.fromJson(Map<String, dynamic> j) => HouseholdMemberItem(
        userId: j['user_id'] as String,
        userName: (j['user_name'] ?? '') as String,
        userEmail: (j['user_email'] ?? '') as String,
        role: (j['role'] ?? 'member') as String,
        joinedAt: DateTime.parse(j['joined_at'] as String),
      );
}

/// Detailed household with member list in GET /households/{id}.
class HouseholdDetailItem {
  final String id;
  final String name;
  final String createdBy;
  final String role;
  final int productCount;
  final DateTime createdAt;
  final List<HouseholdMemberItem> members;

  const HouseholdDetailItem({
    required this.id,
    required this.name,
    required this.createdBy,
    required this.role,
    required this.productCount,
    required this.createdAt,
    required this.members,
  });

  factory HouseholdDetailItem.fromJson(Map<String, dynamic> j) => HouseholdDetailItem(
        id: j['id'] as String,
        name: (j['name'] ?? '') as String,
        createdBy: j['created_by'] as String,
        role: (j['role'] ?? 'member') as String,
        productCount: (j['product_count'] ?? 0) as int,
        createdAt: DateTime.parse(j['created_at'] as String),
        members: ((j['members'] ?? const <dynamic>[]) as List)
            .cast<Map<String, dynamic>>()
            .map(HouseholdMemberItem.fromJson)
            .toList(),
      );
}

/// Household invite representation.
class HouseholdInviteItem {
  final String id;
  final String householdId;
  final String code;
  final String role;
  final DateTime expiresAt;
  final DateTime? usedAt;
  final DateTime createdAt;

  const HouseholdInviteItem({
    required this.id,
    required this.householdId,
    required this.code,
    required this.role,
    required this.expiresAt,
    this.usedAt,
    required this.createdAt,
  });

  factory HouseholdInviteItem.fromJson(Map<String, dynamic> j) => HouseholdInviteItem(
        id: j['id'] as String,
        householdId: j['household_id'] as String,
        code: j['code'] as String,
        role: (j['role'] ?? 'member') as String,
        expiresAt: DateTime.parse(j['expires_at'] as String),
        usedAt: j['used_at'] != null ? DateTime.tryParse(j['used_at'] as String) : null,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

/// Official brand support portal and contacts.
class BrandSupportItem {
  final String brand;
  final String category;
  final String supportPhone;
  final String supportUrl;
  final String claimPortalUrl;
  final String? warrantyCheckUrl;
  final String? serialLookupUrl;
  final String supportHours;
  final String? notes;

  const BrandSupportItem({
    required this.brand,
    required this.category,
    required this.supportPhone,
    required this.supportUrl,
    required this.claimPortalUrl,
    this.warrantyCheckUrl,
    this.serialLookupUrl,
    this.supportHours = 'Mon-Fri 9am-6pm local time',
    this.notes,
  });

  factory BrandSupportItem.fromJson(Map<String, dynamic> j) => BrandSupportItem(
        brand: (j['brand'] ?? '') as String,
        category: (j['category'] ?? '') as String,
        supportPhone: (j['support_phone'] ?? '') as String,
        supportUrl: (j['support_url'] ?? '') as String,
        claimPortalUrl: (j['claim_portal_url'] ?? '') as String,
        warrantyCheckUrl: j['warranty_check_url'] as String?,
        serialLookupUrl: j['serial_lookup_url'] as String?,
        supportHours: (j['support_hours'] ?? 'Mon-Fri 9am-6pm') as String,
        notes: j['notes'] as String?,
      );
}

/// Warranty claim item.
class WarrantyClaimItem {
  final String id;
  final String productId;
  final String productName;
  final String? productBrand;
  final String? productSerial;
  final String? warrantyId;
  final String? warrantyProvider;
  final String? claimReference;
  final String title;
  final String issueDescription;
  final String status;
  final DateTime incidentDate;
  final String? resolutionNotes;
  final double? claimCostCovered;
  final String? contactEmail;
  final String? contactPhone;
  final DateTime createdAt;
  final DateTime updatedAt;
  final BrandSupportItem? brandSupport;

  const WarrantyClaimItem({
    required this.id,
    required this.productId,
    required this.productName,
    this.productBrand,
    this.productSerial,
    this.warrantyId,
    this.warrantyProvider,
    this.claimReference,
    required this.title,
    required this.issueDescription,
    required this.status,
    required this.incidentDate,
    this.resolutionNotes,
    this.claimCostCovered,
    this.contactEmail,
    this.contactPhone,
    required this.createdAt,
    required this.updatedAt,
    this.brandSupport,
  });

  factory WarrantyClaimItem.fromJson(Map<String, dynamic> j) => WarrantyClaimItem(
        id: j['id'] as String,
        productId: j['product_id'] as String,
        productName: (j['product_name'] ?? '') as String,
        productBrand: j['product_brand'] as String?,
        productSerial: j['product_serial'] as String?,
        warrantyId: j['warranty_id'] as String?,
        warrantyProvider: j['warranty_provider'] as String?,
        claimReference: j['claim_reference'] as String?,
        title: (j['title'] ?? '') as String,
        issueDescription: (j['issue_description'] ?? '') as String,
        status: (j['status'] ?? 'draft') as String,
        incidentDate: DateTime.parse(j['incident_date'] as String),
        resolutionNotes: j['resolution_notes'] as String?,
        claimCostCovered: (j['claim_cost_covered'] as num?)?.toDouble(),
        contactEmail: j['contact_email'] as String?,
        contactPhone: j['contact_phone'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
        updatedAt: DateTime.parse(j['updated_at'] as String),
        brandSupport: j['brand_support'] != null
            ? BrandSupportItem.fromJson(j['brand_support'] as Map<String, dynamic>)
            : null,
      );
}

/// Compiled warranty claim dossier with attached documents and formatted markdown.
class ClaimDossierItem {
  final String dossierId;
  final DateTime generatedAt;
  final WarrantyClaimItem claim;
  final Map<String, dynamic> product;
  final Map<String, dynamic>? warranty;
  final List<Map<String, dynamic>> documents;
  final List<Map<String, dynamic>> repairs;
  final BrandSupportItem? brandSupport;
  final Map<String, dynamic> claimant;
  final String formattedMarkdown;

  const ClaimDossierItem({
    required this.dossierId,
    required this.generatedAt,
    required this.claim,
    required this.product,
    this.warranty,
    this.documents = const [],
    this.repairs = const [],
    this.brandSupport,
    required this.claimant,
    required this.formattedMarkdown,
  });

  factory ClaimDossierItem.fromJson(Map<String, dynamic> j) => ClaimDossierItem(
        dossierId: j['dossier_id'] as String,
        generatedAt: DateTime.parse(j['generated_at'] as String),
        claim: WarrantyClaimItem.fromJson(j['claim'] as Map<String, dynamic>),
        product: (j['product'] ?? const <String, dynamic>{}) as Map<String, dynamic>,
        warranty: j['warranty'] as Map<String, dynamic>?,
        documents: ((j['documents'] ?? const <dynamic>[]) as List)
            .cast<Map<String, dynamic>>(),
        repairs: ((j['repairs'] ?? const <dynamic>[]) as List)
            .cast<Map<String, dynamic>>(),
        brandSupport: j['brand_support'] != null
            ? BrandSupportItem.fromJson(j['brand_support'] as Map<String, dynamic>)
            : null,
        claimant: (j['claimant'] ?? const <String, dynamic>{}) as Map<String, dynamic>,
        formattedMarkdown: (j['formatted_markdown'] ?? '') as String,
      );
}