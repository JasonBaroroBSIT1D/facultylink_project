import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_config.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({String? baseUrl, http.Client? httpClient})
      : baseUrl = baseUrl ?? apiBaseUrlCandidates().first,
        _http = httpClient ?? http.Client();

  static String get defaultBaseUrl => apiBaseUrlCandidates().first;

  static const Duration timeout = Duration(seconds: 4);

  String baseUrl;
  final http.Client _http;
  String? accessToken;

  Map<String, String> get _headers {
    return {
      'Accept': 'application/json',
      if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    };
  }

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<T> _withTimeout<T>(Future<T> future) {
    return future.timeout(
      timeout,
      onTimeout: () => throw TimeoutException('FacultyLink API timed out.'),
    );
  }

  Future<dynamic> getJson(String path) async {
    final response = await _withTimeout(_http.get(_uri(path), headers: _headers));
    return _decode(response);
  }

  Future<dynamic> sendJson(
    String method,
    String path, [
    Map<String, dynamic>? body,
    Duration? timeout,
  ]) async {
    final request = http.Request(method, _uri(path))
      ..headers.addAll({
        ..._headers,
        'Content-Type': 'application/json',
      });
    if (body != null) request.body = jsonEncode(body);
    final streamed = timeout == null
        ? await _withTimeout(_http.send(request))
        : await _http.send(request).timeout(
            timeout,
            onTimeout: () => throw TimeoutException('FacultyLink API timed out.'),
          );
    final response = await http.Response.fromStream(streamed);
    return _decode(response);
  }

  /// Finds a reachable API host (same candidates as sign-in) before a request
  /// that must not be repeated, such as sending an email.
  Future<void> _useReachableHost() async {
    final candidates = <String>{baseUrl, ...apiBaseUrlCandidates()};
    for (final candidate in candidates) {
      baseUrl = candidate;
      try {
        await getJson('/');
        return;
      } catch (_) {
        continue;
      }
    }
    throw ApiException(
      'Cannot reach the FacultyLink API. Keep Flask running and stay on the same Wi‑Fi as the computer.',
    );
  }

  Future<Map<String, dynamic>> _recoveryCall(
    String step,
    Map<String, dynamic> body, {
    Duration timeout = const Duration(seconds: 12),
  }) async {
    await _useReachableHost();
    try {
      final data = await sendJson(
        'POST',
        '/api/auth/forgot-password/$step',
        body,
        timeout,
      );
      return data as Map<String, dynamic>;
    } on TimeoutException {
      throw ApiException('The server took too long to respond. Please try again.');
    }
  }

  /// Emails a 6-digit code. The server answers the same for unknown emails.
  Future<Map<String, dynamic>> requestPasswordResetCode(String email) =>
      _recoveryCall(
        'request',
        {'email': email.trim()},
        timeout: const Duration(seconds: 30),
      );

  /// Returns a short-lived reset token when the code is correct.
  Future<String> verifyPasswordResetCode(String email, String otp) async {
    final data = await _recoveryCall('verify', {'email': email.trim(), 'otp': otp});
    return data['resetToken'] as String;
  }

  Future<String> resetPassword({
    required String email,
    required String resetToken,
    required String newPassword,
  }) async {
    final data = await _recoveryCall('reset', {
      'email': email.trim(),
      'resetToken': resetToken,
      'newPassword': newPassword,
    });
    return (data['message'] as String?) ?? 'Your password has been updated.';
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    await sendJson('POST', '/api/auth/change-password', {
      'currentPassword': currentPassword,
      'newPassword': newPassword,
    });
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final payload = {
      'email': email.trim(),
      'password': password,
    };
    Object? lastError;
    for (final candidate in apiBaseUrlCandidates()) {
      baseUrl = candidate;
      try {
        final data = await sendJson('POST', '/api/auth/login', payload) as Map<String, dynamic>;
        accessToken = data['accessToken'] as String?;
        return data;
      } on ApiException {
        rethrow;
      } catch (error) {
        lastError = error;
      }
    }
    throw ApiException(
      lastError is ApiException
          ? lastError.message
          : 'Cannot reach the FacultyLink API. Keep Flask running and stay on the same Wi‑Fi as the computer.',
    );
  }

  Future<String> register({required String fullName, required String email}) async {
    final data = await sendJson('POST', '/api/auth/register', {
      'fullName': fullName,
      'email': email,
    }) as Map<String, dynamic>;
    return (data['message'] as String?) ??
        'Faculty accounts are issued by your institution. This request was recorded.';
  }

  Future<Map<String, dynamic>> uploadDocument({
    required String title,
    required String category,
    required String kra,
    required String fileName,
    String? criterionId,
    String? indicatorId,
    double? contributionPercent,
    String? packageId,
    int? requirementIndex,
    List<int>? fileBytes,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/api/documents'))
      ..headers.addAll(_headers)
      ..fields.addAll({
        'title': title,
        'category': category,
        'kra': kra,
        'fileName': fileName,
        if (criterionId != null && criterionId.isNotEmpty) 'criterionId': criterionId,
        if (indicatorId != null && indicatorId.isNotEmpty) 'indicatorId': indicatorId,
        if (contributionPercent != null) 'contributionPercent': contributionPercent.toString(),
        if (packageId != null && packageId.isNotEmpty) 'packageId': packageId,
        if (requirementIndex != null) 'requirementIndex': requirementIndex.toString(),
      });

    if (fileBytes != null) {
      request.files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: fileName));
    }

    final streamed = await _http.send(request).timeout(
      const Duration(seconds: 90),
      onTimeout: () => throw TimeoutException('Upload timed out.'),
    );
    final response = await http.Response.fromStream(streamed);
    return _decode(response) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> kraCatalog() async {
    final data = await getJson('/api/kra-catalog');
    return data is Map<String, dynamic> ? data : {'kras': []};
  }

  Future<void> deleteDocument(String publicId) async {
    await sendJson('DELETE', '/api/documents/$publicId');
  }

  Future<Map<String, dynamic>> replaceDocument({
    required String publicId,
    required String fileName,
    required List<int> fileBytes,
    String? title,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/api/documents/$publicId/replace'))
      ..headers.addAll(_headers)
      ..fields.addAll({
        'fileName': fileName,
        if (title != null && title.isNotEmpty) 'title': title,
      })
      ..files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: fileName));
    final streamed = await _http.send(request).timeout(
      const Duration(seconds: 90),
      onTimeout: () => throw TimeoutException('Replace upload timed out.'),
    );
    final response = await http.Response.fromStream(streamed);
    return _decode(response) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> requestDocumentWithdrawal({
    required String publicId,
    String? reason,
  }) async {
    final data = await sendJson('POST', '/api/documents/$publicId/withdraw', {
      if (reason != null && reason.isNotEmpty) 'reason': reason,
    });
    return data is Map<String, dynamic> ? data : {'ok': true};
  }

  Future<List<int>> downloadDocumentBytes(String publicId) async {
    final path = '/api/documents/$publicId/file';
    final candidates = <String>{
      baseUrl,
      ...apiBaseUrlCandidates(),
    }.toList();

    Object? lastNetworkError;
    ApiException? lastApiError;

    for (final candidate in candidates) {
      baseUrl = candidate;
      try {
        final response = await _http
            .get(_uri(path), headers: _headers)
            .timeout(
              const Duration(seconds: 90),
              onTimeout: () => throw TimeoutException('File download timed out.'),
            );
        if (response.statusCode >= 400) {
          String message = 'Could not download the original file.';
          try {
            final decoded = jsonDecode(response.body.isEmpty ? '{}' : response.body);
            if (decoded is Map && decoded['error'] != null) {
              message = decoded['error'].toString();
            } else if (response.statusCode == 401) {
              message = 'Sign in again to open this file.';
            } else if (response.statusCode == 404) {
              message = 'Original file is not available on the server.';
            }
          } catch (_) {
            // Keep default message.
          }
          lastApiError = ApiException(message, statusCode: response.statusCode);
          // Auth / not-found will fail the same on every host — stop early.
          if (response.statusCode == 401 ||
              response.statusCode == 403 ||
              response.statusCode == 404) {
            throw lastApiError;
          }
          continue;
        }
        return response.bodyBytes;
      } on ApiException {
        rethrow;
      } catch (error) {
        lastNetworkError = error;
      }
    }

    if (lastApiError != null) throw lastApiError;
    throw ApiException(
      lastNetworkError is TimeoutException
          ? 'File download timed out. Confirm Flask is running on port 5000.'
          : 'Cannot reach the FacultyLink API from this phone. Stay on Wi‑Fi $lanApiHost (same network as the PC), keep Flask running, or reconnect USB and run: adb reverse tcp:5000 tcp:5000',
    );
  }

  dynamic _decode(http.Response response) {
    final raw = response.body.isEmpty ? '{}' : response.body;
    final decoded = jsonDecode(raw);
    if (response.statusCode >= 400) {
      final message = decoded is Map && decoded['error'] != null
          ? decoded['error'].toString()
          : 'Request failed (${response.statusCode}).';
      throw ApiException(message, statusCode: response.statusCode);
    }
    return decoded;
  }
}
