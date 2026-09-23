import 'dart:convert';

import 'package:ownly/core/constants/api_constants.dart';

/// Parsed notification payload containing routing and subject metadata.
class NotificationPayload {
  final String route;
  final String? deepLink;
  final String? title;
  final String? body;
  final String? subjectType;
  final String? subjectId;
  final String? productId;

  const NotificationPayload({
    required this.route,
    this.deepLink,
    this.title,
    this.body,
    this.subjectType,
    this.subjectId,
    this.productId,
  });

  /// Parse from raw string payload (JSON string or URI string).
  factory NotificationPayload.parse(String? raw) {
    if (raw == null || raw.trim().isEmpty) {
      return const NotificationPayload(route: OwnlyRoutes.today);
    }

    final trimmed = raw.trim();

    // 1. Try parsing as JSON object
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        final map = jsonDecode(trimmed) as Map<String, dynamic>;
        final route = _normalizeRoute(
          map['route'] as String? ??
              map['deep_link'] as String? ??
              (map['product_id'] != null
                  ? OwnlyRoutes.productPath(map['product_id'].toString())
                  : null),
        );
        return NotificationPayload(
          route: route,
          deepLink: map['deep_link'] as String?,
          title: map['title'] as String?,
          body: map['body'] as String?,
          subjectType: map['subject_type'] as String?,
          subjectId: map['subject_id']?.toString(),
          productId: map['product_id']?.toString(),
        );
      } catch (_) {
        // Fallback to plain string URL parser below
      }
    }

    // 2. Parse as URI / path string
    return NotificationPayload(
      route: _normalizeRoute(trimmed),
      deepLink: trimmed.startsWith('${OwnlyRoutes.scheme}:') ? trimmed : null,
    );
  }

  /// Normalizes incoming deep links (`ownly:///products/123`, `ownly://reminders`, `/products/123`)
  /// into canonical GoRouter paths.
  static String _normalizeRoute(String? raw) {
    if (raw == null || raw.trim().isEmpty) {
      return OwnlyRoutes.today;
    }

    var path = raw.trim();

    // Strip scheme if present: ownly:///products/123 or ownly://products/123
    if (path.startsWith('${OwnlyRoutes.scheme}:///')) {
      path = path.substring('${OwnlyRoutes.scheme}://'.length);
    } else if (path.startsWith('${OwnlyRoutes.scheme}://')) {
      path = path.substring('${OwnlyRoutes.scheme}:/'.length);
    }

    // Ensure leading slash
    if (!path.startsWith('/')) {
      path = '/$path';
    }

    // Strip trailing slashes (except root)
    if (path.length > 1 && path.endsWith('/')) {
      path = path.substring(0, path.length - 1);
    }

    // Route alias mapping
    if (path == '/dashboard') {
      return OwnlyRoutes.today;
    }

    return path;
  }

  Map<String, dynamic> toJson() => {
        'route': route,
        if (deepLink != null) 'deep_link': deepLink,
        if (title != null) 'title': title,
        if (body != null) 'body': body,
        if (subjectType != null) 'subject_type': subjectType,
        if (subjectId != null) 'subject_id': subjectId,
        if (productId != null) 'product_id': productId,
      };

  @override
  String toString() => 'NotificationPayload(route: $route, subjectType: $subjectType)';
}
