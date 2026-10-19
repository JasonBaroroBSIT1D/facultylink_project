import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/enums.dart';
import '../models/models.dart';
import '../services/api_client.dart';
import '../services/api_mappers.dart';
import 'mock_data.dart';

/// App-wide faculty state. Uses the Flask API after login; mock data otherwise
/// so widget tests and offline previews still render Maria Santos.
class AppState extends ChangeNotifier {
  AppState._()
      : faculty = MockData.faculty,
        documents = List<FacultyDocument>.from(MockData.documents),
        notifications = List<AppNotification>.from(MockData.notifications);

  static final AppState instance = AppState._();

  ApiClient? _api;
  FlutterSecureStorage? _storage;

  ApiClient get api => _api ??= ApiClient();

  @visibleForTesting
  set api(ApiClient? client) => _api = client;
  FlutterSecureStorage get _tokenStorage =>
      _storage ??= const FlutterSecureStorage();

  FacultyProfile faculty;
  List<FacultyDocument> documents;
  List<AppNotification> notifications;

  DashboardSnapshot? _dashboard;
  List<KraScore>? _kraScores;
  RankSimulation? _simulation;
  List<RequirementItem>? _requirements;
  PreparationPeriod? _preparationPeriod;
  bool usingApi = false;
  bool mustChangePassword = false;

  int mainTabIndex = 0;
  int assessmentTabIndex = 0;

  DashboardSnapshot get dashboard => _dashboard ?? MockData.dashboard;
  List<KraScore> get kraScores => _kraScores ?? MockData.kraScores;
  RankSimulation get simulation => _simulation ?? MockData.simulation;
  List<RequirementItem> get requirements => _requirements ?? MockData.requirements;
  PreparationPeriod get preparationPeriod =>
      _preparationPeriod ?? MockData.preparationPeriod;

  int get unreadNotificationCount => notifications
      .where((n) => n.visualState != NotificationVisualState.read)
      .length;

  int get validatedCount =>
      documents.where((d) => d.status == DocumentStatus.validated).length;

  int get pendingCount =>
      documents.where((d) => d.status == DocumentStatus.pendingReview).length;

  int get actionRequiredCount => documents
      .where((d) =>
          d.status == DocumentStatus.needsRevision ||
          d.status == DocumentStatus.invalid)
      .length;

  void setMainTab(int index) {
    if (mainTabIndex == index) return;
    mainTabIndex = index;
    notifyListeners();
  }

  void openAssessment({int innerTab = 0}) {
    assessmentTabIndex = innerTab;
    notifyListeners();
  }

  void openSimulation() {
    mainTabIndex = 2;
    notifyListeners();
  }

  void openDocuments() {
    mainTabIndex = 1;
    notifyListeners();
  }

  void openNotifications() {
    mainTabIndex = 3;
    notifyListeners();
  }

  void openProfile() {
    mainTabIndex = 4;
    notifyListeners();
  }

  void setAssessmentTab(int index) {
    if (assessmentTabIndex == index) return;
    assessmentTabIndex = index;
    notifyListeners();
  }

  FacultyDocument? documentById(String id) {
    for (final doc in documents) {
      if (doc.id == id) return doc;
    }
    return null;
  }

  KraScore kraScore(KraType type) {
    return kraScores.firstWhere((k) => k.type == type);
  }

  Future<void> login(String email, String password) async {
    final data = await api.login(email, password);
    usingApi = true;
    mustChangePassword = data['mustChangePassword'] == true;
    await _tokenStorage.write(key: 'accessToken', value: api.accessToken);
    faculty = profileFromJson(data['profile'] as Map<String, dynamic>);
    if (!mustChangePassword) {
      await refreshFromApi();
    }
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    await api.changePassword(
      currentPassword: currentPassword,
      newPassword: newPassword,
    );
    mustChangePassword = false;
    await refreshFromApi();
  }

  Future<String> requestAccount({required String fullName, required String email}) {
    return api.register(fullName: fullName, email: email);
  }

  Future<void> refreshFromApi() async {
    if (!usingApi || api.accessToken == null) return;
    final results = await Future.wait([
      api.getJson('/api/me'),
      api.getJson('/api/documents'),
      api.getJson('/api/notifications'),
      api.getJson('/api/assessment/kra-scores'),
      api.getJson('/api/assessment/requirements'),
      api.getJson('/api/simulation'),
      api.getJson('/api/preparation-period'),
      api.getJson('/api/dashboard'),
    ]);

    faculty = profileFromJson(results[0] as Map<String, dynamic>);
    documents = [
      for (final item in results[1] as List)
        if (item is Map<String, dynamic>) documentFromJson(item),
    ];
    notifications = [
      for (final item in results[2] as List)
        if (item is Map<String, dynamic>) notificationFromJson(item),
    ];
    _kraScores = [
      for (final item in results[3] as List)
        if (item is Map<String, dynamic>) kraScoreFromJson(item),
    ];
    _requirements = [
      for (final item in results[4] as List)
        if (item is Map<String, dynamic>) requirementFromJson(item),
    ];
    _simulation = simulationFromJson(results[5] as Map<String, dynamic>);
    _preparationPeriod = periodFromJson(results[6] as Map<String, dynamic>);
    _dashboard = dashboardFromJson(results[7] as Map<String, dynamic>);
    notifyListeners();
  }

  Future<void> uploadDocument({
    required String title,
    required DocumentCategory category,
    required KraType kra,
    required String fileName,
    String? criterionId,
    String? indicatorId,
    double? contributionPercent,
    List<int>? fileBytes,
  }) async {
    if (usingApi) {
      final created = await api.uploadDocument(
        title: title,
        category: category.name,
        kra: kra.name,
        fileName: fileName,
        criterionId: criterionId,
        indicatorId: indicatorId,
        contributionPercent: contributionPercent,
        fileBytes: fileBytes,
      );
      final doc = documentFromJson(created);
      documents = [doc, ...documents];
      await refreshFromApi();
      return;
    }

    addSubmittedDocument(
      FacultyDocument(
        id: 'doc-${DateTime.now().millisecondsSinceEpoch}',
        title: title,
        category: category,
        kra: kra,
        submittedAt: DateTime.now(),
        status: DocumentStatus.pendingReview,
        points: 0,
        fileName: fileName,
        criterionId: criterionId,
        indicatorId: indicatorId,
        hasFile: fileBytes != null,
        extractedInfo: const {
          'Status': 'Queued for processing',
        },
        validationResult: 'Submitted. Awaiting system processing and reviewer validation.',
      ),
    );
  }

  void markNotificationRead(String id) {
    notifications = [
      for (final n in notifications)
        if (n.id == id)
          n.copyWith(visualState: NotificationVisualState.read)
        else
          n,
    ];
    notifyListeners();
    if (usingApi) {
      _forget(api.sendJson('POST', '/api/notifications/$id/read'));
    }
  }

  void markAllNotificationsRead() {
    notifications = [
      for (final n in notifications)
        n.copyWith(visualState: NotificationVisualState.read),
    ];
    notifyListeners();
    if (usingApi) {
      _forget(api.sendJson('POST', '/api/notifications/read-all'));
    }
  }

  void clearNotifications() {
    notifications = [];
    notifyListeners();
    if (usingApi) {
      _forget(api.sendJson('DELETE', '/api/notifications'));
    }
  }

  void addSubmittedDocument(FacultyDocument document) {
    documents = [document, ...documents];
    notifications = [
      AppNotification(
        id: 'n-${DateTime.now().millisecondsSinceEpoch}',
        kind: NotificationKind.documentSubmitted,
        message: '${document.title} was submitted and is pending review.',
        createdAt: DateTime.now(),
        visualState: NotificationVisualState.unread,
        relatedDocumentId: document.id,
        relatedKra: document.kra,
      ),
      ...notifications,
    ];
    notifyListeners();
  }

  void updateFaculty(FacultyProfile updated) {
    faculty = updated;
    notifyListeners();
    if (usingApi) {
      _forget(api.sendJson('PATCH', '/api/me/profile', {
        'fullName': updated.fullName,
        'email': updated.email,
        'phone': updated.phone,
        'department': updated.department,
      }));
    }
  }

  Future<void> saveFaculty(FacultyProfile updated) async {
    faculty = updated;
    notifyListeners();
    if (usingApi) {
      final data = await api.sendJson('PATCH', '/api/me/profile', {
        'fullName': updated.fullName,
        'email': updated.email,
        'phone': updated.phone,
        'department': updated.department,
      }) as Map<String, dynamic>;
      faculty = profileFromJson(data);
      notifyListeners();
    }
  }

  Future<void> resetSession() async {
    mainTabIndex = 0;
    assessmentTabIndex = 0;
    usingApi = false;
    api.accessToken = null;
    if (_storage != null) {
      await _tokenStorage.delete(key: 'accessToken');
    }
    faculty = MockData.faculty;
    documents = List<FacultyDocument>.from(MockData.documents);
    notifications = List<AppNotification>.from(MockData.notifications);
    _dashboard = null;
    _kraScores = null;
    _simulation = null;
    _requirements = null;
    _preparationPeriod = null;
    notifyListeners();
  }
}

void _forget(Future<dynamic> future) {
  unawaited(future.catchError((_) => null));
}
