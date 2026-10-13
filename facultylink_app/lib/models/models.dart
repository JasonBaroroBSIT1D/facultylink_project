import 'enums.dart';

class FacultyProfile {
  const FacultyProfile({
    required this.fullName,
    required this.facultyId,
    required this.email,
    required this.department,
    required this.college,
    required this.currentRank,
    required this.highestDegree,
    required this.specialization,
    required this.yearsInService,
    required this.employmentStatus,
    required this.campus,
    required this.phone,
  });

  final String fullName;
  final String facultyId;
  final String email;
  final String department;
  final String college;
  final String currentRank;
  final String highestDegree;
  final String specialization;
  final int yearsInService;
  final String employmentStatus;
  final String campus;
  final String phone;

  String get firstName => fullName.split(' ').first;

  FacultyProfile copyWith({
    String? fullName,
    String? email,
    String? department,
    String? phone,
  }) {
    return FacultyProfile(
      fullName: fullName ?? this.fullName,
      facultyId: facultyId,
      email: email ?? this.email,
      department: department ?? this.department,
      college: college,
      currentRank: currentRank,
      highestDegree: highestDegree,
      specialization: specialization,
      yearsInService: yearsInService,
      employmentStatus: employmentStatus,
      campus: campus,
      phone: phone ?? this.phone,
    );
  }
}

class KraScore {
  const KraScore({
    required this.type,
    required this.currentPoints,
    required this.targetPoints,
    required this.documentCount,
    required this.statusLabel,
    required this.breakdown,
  });

  final KraType type;
  final int currentPoints;
  final int targetPoints;
  final int documentCount;
  final String statusLabel;
  final List<KraBreakdownItem> breakdown;

  double get progress =>
      targetPoints == 0 ? 0 : (currentPoints / targetPoints).clamp(0, 1);
}

class KraBreakdownItem {
  const KraBreakdownItem({
    required this.title,
    required this.points,
    required this.note,
  });

  final String title;
  final int points;
  final String note;
}

class FacultyDocument {
  const FacultyDocument({
    required this.id,
    required this.title,
    required this.category,
    required this.kra,
    required this.submittedAt,
    required this.status,
    required this.points,
    required this.fileName,
    this.author,
    this.extractedInfo = const {},
    this.reviewerFeedback,
    this.validationResult,
  });

  final String id;
  final String title;
  final DocumentCategory category;
  final KraType kra;
  final DateTime submittedAt;
  final DocumentStatus status;
  final int points;
  final String fileName;
  final String? author;
  final Map<String, String> extractedInfo;
  final String? reviewerFeedback;
  final String? validationResult;

  bool get canResubmit =>
      status == DocumentStatus.needsRevision ||
      status == DocumentStatus.invalid;

  bool get requiresAction => status == DocumentStatus.needsRevision;
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.kind,
    required this.message,
    required this.createdAt,
    required this.visualState,
    this.relatedDocumentId,
    this.relatedKra,
  });

  final String id;
  final NotificationKind kind;
  final String message;
  final DateTime createdAt;
  final NotificationVisualState visualState;
  final String? relatedDocumentId;
  final KraType? relatedKra;

  String get title => kind.title;

  AppNotification copyWith({NotificationVisualState? visualState}) {
    return AppNotification(
      id: id,
      kind: kind,
      message: message,
      createdAt: createdAt,
      visualState: visualState ?? this.visualState,
      relatedDocumentId: relatedDocumentId,
      relatedKra: relatedKra,
    );
  }
}

class RequirementItem {
  const RequirementItem({
    required this.id,
    required this.title,
    required this.description,
    required this.kra,
    required this.status,
    this.hint,
  });

  final String id;
  final String title;
  final String description;
  final KraType kra;
  final RequirementStatus status;
  final String? hint;
}

class ImprovementArea {
  const ImprovementArea({
    required this.kra,
    required this.recommendedPoints,
    required this.guidance,
  });

  final KraType kra;
  final int recommendedPoints;
  final String guidance;
}

class RankSimulation {
  const RankSimulation({
    required this.currentRank,
    required this.targetRank,
    required this.currentPoints,
    required this.requiredPoints,
    required this.eligibilityLabel,
    required this.areasToImprove,
  });

  final String currentRank;
  final String targetRank;
  final int currentPoints;
  final int requiredPoints;
  final String eligibilityLabel;
  final List<ImprovementArea> areasToImprove;

  double get progress =>
      requiredPoints == 0 ? 0 : (currentPoints / requiredPoints).clamp(0, 1);

  int get remainingPoints =>
      (requiredPoints - currentPoints).clamp(0, requiredPoints);
}

class RecentActivity {
  const RecentActivity({
    required this.title,
    required this.subtitle,
    required this.timeLabel,
    required this.status,
  });

  final String title;
  final String subtitle;
  final String timeLabel;
  final DocumentStatus status;
}

class ReviewerFeedbackPreview {
  const ReviewerFeedbackPreview({
    required this.documentTitle,
    required this.message,
    required this.timeLabel,
  });

  final String documentTitle;
  final String message;
  final String timeLabel;
}

class PreparationPeriod {
  const PreparationPeriod({
    required this.cycleName,
    required this.startDate,
    required this.endDate,
    required this.reviewerAvailableUntil,
    required this.status,
  });

  final String cycleName;
  final DateTime startDate;
  final DateTime endDate;
  final DateTime reviewerAvailableUntil;
  final PreparationPeriodStatus status;
}

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.totalPoints,
    required this.targetPoints,
    required this.documentCompletionPercent,
    required this.validatedCount,
    required this.pendingCount,
    required this.actionRequiredCount,
    required this.kraScores,
    required this.recentActivity,
    required this.recentFeedback,
    required this.simulation,
  });

  final int totalPoints;
  final int targetPoints;
  final int documentCompletionPercent;
  final int validatedCount;
  final int pendingCount;
  final int actionRequiredCount;
  final List<KraScore> kraScores;
  final List<RecentActivity> recentActivity;
  final List<ReviewerFeedbackPreview> recentFeedback;
  final RankSimulation simulation;

  double get overallProgress =>
      targetPoints == 0 ? 0 : (totalPoints / targetPoints).clamp(0, 1);
}
