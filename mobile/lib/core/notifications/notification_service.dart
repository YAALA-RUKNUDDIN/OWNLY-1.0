import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:ownly/core/network/token_storage.dart';
import 'package:ownly/core/notifications/notification_payload.dart';
import 'package:ownly/data/repositories.dart';

/// Notification Service for OWNLY.
///
/// Manages local notifications, device registration with the backend,
/// and tap-through routing dispatch (Phase 5).
class NotificationService {
  final FlutterLocalNotificationsPlugin _plugin;
  final TokenStorage _tokenStorage;

  final _tappedController = StreamController<NotificationPayload>.broadcast();
  NotificationPayload? _launchPayload;
  bool _initialized = false;

  NotificationService({
    FlutterLocalNotificationsPlugin? plugin,
    required TokenStorage tokenStorage,
  })  : _plugin = plugin ?? FlutterLocalNotificationsPlugin(),
        _tokenStorage = tokenStorage;

  /// Stream of notification tap events when app is foregrounded or resumed.
  Stream<NotificationPayload> get onNotificationTapped =>
      _tappedController.stream;

  /// Payload that launched the app from a terminated cold-start, if any.
  NotificationPayload? get launchPayload => _launchPayload;

  /// Consumes and clears the cold-start launch payload so it isn't re-routed.
  NotificationPayload? consumeLaunchPayload() {
    final payload = _launchPayload;
    _launchPayload = null;
    return payload;
  }

  /// Initialize the notification plugin, android channel, and tap callbacks.
  Future<void> initialize({
    void Function(NotificationPayload payload)? onTapped,
  }) async {
    if (_initialized) return;

    if (onTapped != null) {
      _tappedController.stream.listen(onTapped);
    }

    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
      macOS: darwinSettings,
    );

    await _plugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (response) {
        final raw = response.payload;
        if (raw != null && raw.isNotEmpty) {
          final parsed = NotificationPayload.parse(raw);
          _tappedController.add(parsed);
        }
      },
    );

    // Create high-importance alert channel for Android
    if (!kIsWeb && Platform.isAndroid) {
      const channel = AndroidNotificationChannel(
        'ownly_alerts',
        'OWNLY Alerts',
        description: 'Warranties, return windows, and reminder alerts',
        importance: Importance.high,
        playSound: true,
      );

      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(channel);
    }

    // Inspect cold-start launch
    try {
      final launchDetails =
          await _plugin.getNotificationAppLaunchDetails();
      if (launchDetails != null &&
          launchDetails.didNotificationLaunchApp &&
          launchDetails.notificationResponse?.payload != null) {
        _launchPayload = NotificationPayload.parse(
          launchDetails.notificationResponse!.payload,
        );
      }
    } catch (_) {
      // In testing or desktop environments without launch details
    }

    _initialized = true;
  }

  /// Registers the device token with the backend.
  Future<void> registerDeviceToken(OwnlyRepository repo) async {
    try {
      final token = await _tokenStorage.getOrCreateDeviceToken();
      final platform = kIsWeb
          ? 'web'
          : Platform.isAndroid
              ? 'android'
              : Platform.isIOS
                  ? 'ios'
                  : 'desktop';
      await repo.registerDevice(token, platform: platform);
    } catch (e) {
      debugPrint('Failed to register device token: $e');
    }
  }

  /// Unregisters the device token with the backend (e.g. on user logout).
  Future<void> unregisterDeviceToken(OwnlyRepository repo) async {
    try {
      final token = await _tokenStorage.getOrCreateDeviceToken();
      await repo.unregisterDevice(token);
    } catch (e) {
      debugPrint('Failed to unregister device token: $e');
    }
  }

  /// Shows a notification immediately in the system tray.
  Future<void> showNotification({
    int? id,
    required String title,
    required String body,
    NotificationPayload? payload,
  }) async {
    if (Platform.environment.containsKey('FLUTTER_TEST')) {
      return;
    }

    const androidDetails = AndroidNotificationDetails(
      'ownly_alerts',
      'OWNLY Alerts',
      channelDescription:
          'Warranties, return windows, and reminder alerts',
      importance: Importance.max,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );

    const darwinDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(
      android: androidDetails,
      iOS: darwinDetails,
      macOS: darwinDetails,
    );

    final payloadString = payload != null
        ? jsonEncode(payload.toJson())
        : null;

    try {
      await _plugin.show(
        id ?? DateTime.now().millisecondsSinceEpoch ~/ 1000,
        title,
        body,
        details,
        payload: payloadString,
      );
    } catch (e) {
      debugPrint('Local notification show: $e');
    }
  }

  void dispose() {
    _tappedController.close();
  }
}

final notificationServiceProvider = Provider<NotificationService>((ref) {
  final service = NotificationService(
    tokenStorage: ref.watch(tokenStorageProvider),
  );
  ref.onDispose(service.dispose);
  return service;
});
