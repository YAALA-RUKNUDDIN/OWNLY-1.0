import 'package:intl/intl.dart';

class Formatters {
  static String date(DateTime d) => DateFormat('MMMM d, yyyy').format(d);

  static String shortDate(DateTime d) => DateFormat('MMM d, yyyy').format(d);

  static String daysRemaining(int days) {
    if (days == 0) return 'today';
    if (days == 1) return 'tomorrow';
    if (days > 0) return 'in $days days';
    return '${-days} days ago';
  }

  static String money(num? amount, String currency) {
    if (amount == null) return '—';
    final symbol = switch (currency) {
      'USD' => r'$',
      'EUR' => '€',
      'GBP' => '£',
      'INR' => '₹',
      _ => '$currency ',
    };
    return '$symbol${amount.toStringAsFixed(amount.truncateToDouble() == amount ? 0 : 2)}';
  }
}