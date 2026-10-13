import '../models/enums.dart';
import '../models/models.dart';

T _enumByName<T extends Enum>(List<T> values, String? raw, T fallback) {
  if (raw == null) return fallback;
  for (final value in values) {
    if (value.name == raw) return value;
  }
  return fallback;
}

DateTime _date(dynamic raw) {
  if (raw is String && raw.isNotEmpty) {
    return DateTime.tryParse(raw) ?? DateTime.now();
  }
  return DateTime.now();
}

Map<String, String> _stringMap(dynamic raw) {
  if (raw is! Map) return {};
  return raw.map((key, value) => MapEntry(key.toString(), value.toString()));
}

FacultyProfile profileFromJson(Map<String, dynamic> json) {
  return FacultyProfile(
    fullName: json['fullName'] as String? ?? '',
    facultyId: json['facultyId'] as String? ?? '',
    email: json['email'] as String? ?? '',
    department: json['department'] as String? ?? '',
    college: json['college'] as String? ?? '',
    currentRank: json['currentRank'] as String? ?? '',
    highestDegree: json['highestDegree'] as String? ?? '',
    specialization: json['specialization'] as String? ?? '',
    yearsInService: (json['yearsInService'] as num?)?.toInt() ?? 0,
    employmentStatus: json['employmentStatus'] as String? ?? '',
    campus: json['campus'] as String? ?? '',
    phone: json['phone'] as String? ?? '',
  );
}

KraScore kraScoreFromJson(Map<String, dynamic> json) {
  final breakdown = <KraBreakdownItem>[];
  final raw = json['breakdown'];
  if (raw is List) {
    for (final item in raw) {
      if (item is Map) {
        breakdown.add(
          KraBreakdownItem(
            title: item['title']?.toString() ?? '',
            points: (item['points'] as num?)?.toInt() ?? 0,
            note: item['note']?.toString() ?? '',
          ),
        );
      }
    }
  }
  return KraScore(
    type: _enumByName(KraType.values, json['type'] as String?, KraType.instruction),
    currentPoints: (json['currentPoints'] as num?)?.toInt() ?? 0,
    targetPoints: (json['targetPoints'] as num?)?.toInt() ?? 0,
    documentCount: (json['documentCount'] as num?)?.toInt() ?? 0,
    statusLabel: json['statusLabel'] as String? ?? 'In progress',
    breakdown: breakdown,
  );
}

FacultyDocument documentFromJson(Map<String, dynamic> json) {
  return FacultyDocument(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    category: _enumByName(
      DocumentCategory.values,
      json['category'] as String?,
      DocumentCategory.teachingRecords,
    ),
    kra: _enumByName(KraType.values, json['kra'] as String?, KraType.instruction),
    submittedAt: _date(json['submittedAt']),
    status: _enumByName(
      DocumentStatus.values,
      json['status'] as String?,
      DocumentStatus.pendingReview,
    ),
    points: (json['points'] as num?)?.toInt() ?? 0,
    fileName: json['fileName'] as String? ?? '',
    author: json['author'] as String?,
    extractedInfo: _stringMap(json['extractedInfo']),
    reviewerFeedback: json['reviewerFeedback'] as String?,
    validationResult: json['validationResult'] as String?,
  );
}

AppNotification notificationFromJson(Map<String, dynamic> json) {
  return AppNotification(
    id: json['id'] as String? ?? '',
    kind: _enumByName(
      NotificationKind.values,
      json['kind'] as String?,
      NotificationKind.documentSubmitted,
    ),
    message: json['message'] as String? ?? '',
    createdAt: _date(json['createdAt']),
    visualState: _enumByName(
      NotificationVisualState.values,
      json['visualState'] as String?,
      NotificationVisualState.unread,
    ),
    relatedDocumentId: json['relatedDocumentId'] as String?,
    relatedKra: json['relatedKra'] == null
        ? null
        : _enumByName(KraType.values, json['relatedKra'] as String?, KraType.instruction),
  );
}

RequirementItem requirementFromJson(Map<String, dynamic> json) {
  return RequirementItem(
    id: json['id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    description: json['description'] as String? ?? '',
    kra: _enumByName(KraType.values, json['kra'] as String?, KraType.instruction),
    status: _enumByName(
      RequirementStatus.values,
      json['status'] as String?,
      RequirementStatus.pending,
    ),
    hint: json['hint'] as String?,
  );
}

RankSimulation simulationFromJson(Map<String, dynamic> json) {
  final areas = <ImprovementArea>[];
  final raw = json['areasToImprove'];
  if (raw is List) {
    for (final item in raw) {
      if (item is Map) {
        areas.add(
          ImprovementArea(
            kra: _enumByName(KraType.values, item['kra']?.toString(), KraType.instruction),
            recommendedPoints: (item['recommendedPoints'] as num?)?.toInt() ?? 0,
            guidance: item['guidance']?.toString() ?? '',
          ),
        );
      }
    }
  }
  return RankSimulation(
    currentRank: json['currentRank'] as String? ?? '',
    targetRank: json['targetRank'] as String? ?? '',
    currentPoints: (json['currentPoints'] as num?)?.toInt() ?? 0,
    requiredPoints: (json['requiredPoints'] as num?)?.toInt() ?? 100,
    eligibilityLabel: json['eligibilityLabel'] as String? ?? 'Pending',
    areasToImprove: areas,
    kraConfigVersion: (json['kraConfigVersion'] as num?)?.toInt() ?? 0,
    scoringFormula: json['scoringFormula'] as String? ??
        'Final Score = Base Points × Contribution Percentage',
  );
}

PreparationPeriod periodFromJson(Map<String, dynamic> json) {
  return PreparationPeriod(
    cycleName: json['cycleName'] as String? ?? '',
    startDate: _date(json['startDate']),
    endDate: _date(json['endDate']),
    reviewerAvailableUntil: _date(json['reviewerAvailableUntil']),
    status: _enumByName(
      PreparationPeriodStatus.values,
      json['status'] as String?,
      PreparationPeriodStatus.open,
    ),
  );
}

DashboardSnapshot dashboardFromJson(Map<String, dynamic> json) {
  return DashboardSnapshot(
    totalPoints: (json['totalPoints'] as num?)?.toInt() ?? 0,
    targetPoints: (json['targetPoints'] as num?)?.toInt() ?? 100,
    documentCompletionPercent: (json['documentCompletionPercent'] as num?)?.toInt() ?? 0,
    validatedCount: (json['validatedCount'] as num?)?.toInt() ?? 0,
    pendingCount: (json['pendingCount'] as num?)?.toInt() ?? 0,
    actionRequiredCount: (json['actionRequiredCount'] as num?)?.toInt() ?? 0,
    kraScores: [
      for (final item in (json['kraScores'] as List? ?? const []))
        if (item is Map<String, dynamic>) kraScoreFromJson(item),
    ],
    recentActivity: [
      for (final item in (json['recentActivity'] as List? ?? const []))
        if (item is Map<String, dynamic>)
          RecentActivity(
            title: item['title'] as String? ?? '',
            subtitle: item['subtitle'] as String? ?? '',
            timeLabel: item['timeLabel'] as String? ?? '',
            status: _enumByName(
              DocumentStatus.values,
              item['status'] as String?,
              DocumentStatus.pendingReview,
            ),
          ),
    ],
    recentFeedback: [
      for (final item in (json['recentFeedback'] as List? ?? const []))
        if (item is Map<String, dynamic>)
          ReviewerFeedbackPreview(
            documentTitle: item['documentTitle'] as String? ?? '',
            message: item['message'] as String? ?? '',
            timeLabel: item['timeLabel'] as String? ?? '',
          ),
    ],
    simulation: json['simulation'] is Map<String, dynamic>
        ? simulationFromJson(json['simulation'] as Map<String, dynamic>)
        : MockSimulationFallback.simulation,
  );
}

/// Used only if the dashboard payload omits simulation.
abstract final class MockSimulationFallback {
  static const simulation = RankSimulation(
    currentRank: 'Instructor I',
    targetRank: 'Instructor II',
    currentPoints: 0,
    requiredPoints: 100,
    eligibilityLabel: 'Pending',
    areasToImprove: [],
  );
}
