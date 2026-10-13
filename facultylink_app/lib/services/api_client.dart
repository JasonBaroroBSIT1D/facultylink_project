import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
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

  Future<dynamic> sendJson(String method, String path, [Map<String, dynamic>? body]) async {
    final request = http.Request(method, _uri(path))
      ..headers.addAll({
        ..._headers,
        'Content-Type': 'application/json',
      });
    if (body != null) request.body = jsonEncode(body);
    final streamed = await _withTimeout(_http.send(request));
    final response = await http.Response.fromStream(streamed);
    return _decode(response);
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
    required String author,
    required String fileName,
    List<int>? fileBytes,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/api/documents'))
      ..headers.addAll(_headers)
      ..fields.addAll({
        'title': title,
        'category': category,
        'kra': kra,
        'author': author,
        'fileName': fileName,
      });

    if (fileBytes != null) {
      request.files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: fileName));
    }

    final streamed = await _withTimeout(_http.send(request));
    final response = await http.Response.fromStream(streamed);
    return _decode(response) as Map<String, dynamic>;
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
