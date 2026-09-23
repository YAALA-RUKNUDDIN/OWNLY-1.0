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