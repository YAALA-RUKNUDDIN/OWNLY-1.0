/// Backend API configuration. Change baseUrl per environment
/// (Android emulator uses 10.0.2.2 to reach the host machine).
class ApiConstants {
  static const String baseUrl = String.fromEnvironment(
    'OWNLY_API_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);
}

/// App-wide route constants. Deep links use the `ownly://` scheme
/// (see android/app/src/main/AndroidManifest.xml and ios/Runner/Info.plist).
class OwnlyRoutes {
  static const scheme = 'ownly';
  static const today = '/today';
  static const products = '/products';
  static const addProduct = '/add';
  static const reminders = '/reminders';
  static const profile = '/profile';
  static const login = '/login';
  static const onboarding = '/onboarding';
  static const subscription = '/subscription';
  static const notifications = '/notifications';
  static const dataExport = '/export';
  static const households = '/households';
  static const claims = '/claims';
  static const portfolio = '/portfolio';

  static String productPath(String id) => '/products/$id';
  static String claimPath(String id) => '/claims/$id';
}
