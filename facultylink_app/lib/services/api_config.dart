import 'package:flutter/foundation.dart';

/// PC Wi-Fi address shown by Flask (`Running on http://192.168.1.27:5000`).
/// Change this if `ipconfig` shows a different Wireless LAN IPv4.
const String lanApiHost = String.fromEnvironment(
  'API_HOST',
  defaultValue: '192.168.1.27',
);

List<String> apiBaseUrlCandidates() {
  final urls = <String>{
    if (kIsWeb) 'http://127.0.0.1:5000',
    if (defaultTargetPlatform == TargetPlatform.android) ...[
      'http://127.0.0.1:5000',
      'http://$lanApiHost:5000',
      'http://10.0.2.2:5000',
    ],
    if (defaultTargetPlatform == TargetPlatform.iOS) 'http://$lanApiHost:5000',
    'http://127.0.0.1:5000',
  };
  return urls.toList();
}
