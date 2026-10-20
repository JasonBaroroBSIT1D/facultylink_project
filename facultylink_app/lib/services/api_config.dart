import 'package:flutter/foundation.dart';

/// PC Wi-Fi address shown by Flask (`Running on http://192.168.1.27:5000`).
/// Change this if `ipconfig` shows a different Wireless LAN IPv4.
const String lanApiHost = String.fromEnvironment(
  'API_HOST',
  defaultValue: '192.168.1.27',
);

List<String> apiBaseUrlCandidates() {
  // Prefer the LAN IP for physical phones. 127.0.0.1 only works with
  // `adb reverse tcp:5000 tcp:5000` and breaks as soon as USB/reverse drops.
  final urls = <String>{
    if (kIsWeb) 'http://127.0.0.1:5000',
    if (defaultTargetPlatform == TargetPlatform.android) ...[
      // USB + `adb reverse tcp:5000 tcp:5000` — try localhost first (fastest while developing).
      'http://127.0.0.1:5000',
      'http://$lanApiHost:5000',
      'http://10.0.2.2:5000',
    ],
    if (defaultTargetPlatform == TargetPlatform.iOS) 'http://$lanApiHost:5000',
    'http://127.0.0.1:5000',
  };
  return urls.toList();
}
