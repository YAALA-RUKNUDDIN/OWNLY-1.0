import 'package:flutter/material.dart';
import 'package:ownly/core/theme/ownly_theme.dart';

class OwnlyCategory {
  final String id;
  final String label;
  final IconData icon;
  const OwnlyCategory(this.id, this.label, this.icon);
}

const List<OwnlyCategory> categories = [
  OwnlyCategory('smartphones', 'Smartphones', Icons.smartphone),
  OwnlyCategory('laptops', 'Laptops', Icons.laptop_mac),
  OwnlyCategory('tablets', 'Tablets', Icons.tablet_mac),
  OwnlyCategory('headphones', 'Headphones', Icons.headphones),
  OwnlyCategory('electronics', 'Electronics', Icons.devices_other),
  OwnlyCategory('home_appliances', 'Home Appliances', Icons.home_repair_service),
  OwnlyCategory('furniture', 'Furniture', Icons.chair),
  OwnlyCategory('vehicles', 'Vehicles', Icons.directions_car),
  OwnlyCategory('watches', 'Watches', Icons.watch),
  OwnlyCategory('cameras', 'Cameras', Icons.camera_alt),
  OwnlyCategory('gaming', 'Gaming', Icons.sports_esports),
  OwnlyCategory('other', 'Other', Icons.category),
];

String categoryLabel(String id) {
  for (final c in categories) {
    if (c.id == id) return c.label;
  }
  return id;
}

IconData categoryIcon(String id) {
  for (final c in categories) {
    if (c.id == id) return c.icon;
  }
  return Icons.category;
}

Color statusColor(String status) {
  switch (status) {
    case 'active':
      return OwnlyTheme.success;
    case 'expiring_soon':
      return OwnlyTheme.warning;
    case 'expired':
      return OwnlyTheme.danger;
    default:
      return OwnlyTheme.muted;
  }
}

String statusLabel(String status) {
  switch (status) {
    case 'active':
      return 'Active';
    case 'expiring_soon':
      return 'Expiring soon';
    case 'expired':
      return 'Expired';
    case 'none':
      return 'No warranty';
    default:
      return status;
  }
}