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