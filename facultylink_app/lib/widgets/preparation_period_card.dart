import 'package:flutter/material.dart';

import '../data/app_state.dart';
import '../models/enums.dart';
import '../models/models.dart';
import '../theme/app_colors.dart';
import '../utils/formatters.dart';

class PreparationPeriodCard extends StatelessWidget {
  const PreparationPeriodCard({super.key, this.compact = false});

  final bool compact;

  static const disclaimer =
      'IMPORTANT: FacultyLink is a preparatory and self-assessment platform. The document validation, KRA scores, rank simulation, and reviewer feedback provided through FacultyLink do not constitute the official DBM–CHED evaluation or final rank upgrade/reclassification decision.';

  @override
  Widget build(BuildContext context) {
    final period = AppState.instance.preparationPeriod;
    final palette = _statusPalette(period.status);

    return Card(
      child: Padding(
        padding: EdgeInsets.all(compact ? 14 : 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.navy.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.event_available_outlined,
                    color: AppColors.navy,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Evaluation Preparation Period',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Preparatory review before official DBM–CHED evaluation',
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.3,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                _StatusChip(status: period.status, palette: palette),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              period.cycleName,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: AppColors.navy,
              ),
            ),
            if (!compact) ...[
              const SizedBox(height: 6),
              const Text(
                'FacultyLink helps you prepare, organize, validate, and assess documentary evidence. This is not the Official Evaluation Period.',
                style: TextStyle(
                  fontSize: 12,
                  height: 1.4,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _DateTile(
                    label: 'Review start',
                    value: formatDisplayDate(period.startDate),
                    icon: Icons.play_circle_outline_rounded,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _DateTile(
                    label: 'Review end',
                    value: formatDisplayDate(period.endDate),
                    icon: Icons.flag_outlined,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _ReviewerAvailability(period: period),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: palette.soft,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(palette.icon, color: palette.color, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      period.status.guidance,
                      style: TextStyle(
                        fontSize: 13,
                        height: 1.4,
                        fontWeight: FontWeight.w600,
                        color: palette.color,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.goldSoft.withValues(alpha: 0.55),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.gold.withValues(alpha: 0.55),
                ),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.priority_high_rounded,
                    color: AppColors.warning,
                    size: 18,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      disclaimer,
                      style: TextStyle(
                        fontSize: 12,
                        height: 1.4,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static _StatusPalette _statusPalette(PreparationPeriodStatus status) {
    switch (status) {
      case PreparationPeriodStatus.open:
        return const _StatusPalette(
          color: AppColors.success,
          soft: AppColors.successSoft,
          icon: Icons.check_circle_outline_rounded,
        );
      case PreparationPeriodStatus.closingSoon:
        return const _StatusPalette(
          color: AppColors.warning,
          soft: AppColors.warningSoft,
          icon: Icons.schedule_rounded,
        );
      case PreparationPeriodStatus.closed:
        return const _StatusPalette(
          color: AppColors.error,
          soft: AppColors.errorSoft,
          icon: Icons.lock_outline_rounded,
        );
    }
  }
}

class _StatusPalette {
  const _StatusPalette({
    required this.color,
    required this.soft,
    required this.icon,
  });

  final Color color;
  final Color soft;
  final IconData icon;
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status, required this.palette});

  final PreparationPeriodStatus status;
  final _StatusPalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: palette.soft,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.color.withValues(alpha: 0.35)),
      ),
      child: Text(
        status.label,
        style: TextStyle(
          color: palette.color,
          fontWeight: FontWeight.w800,
          fontSize: 11,
        ),
      ),
    );
  }
}

class _DateTile extends StatelessWidget {
  const _DateTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: AppColors.navy),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              height: 1.25,
            ),
          ),
        ],
      ),
    );
  }
}

class _ReviewerAvailability extends StatelessWidget {
  const _ReviewerAvailability({required this.period});

  final PreparationPeriod period;

  @override
  Widget build(BuildContext context) {
    final available = period.status != PreparationPeriodStatus.closed;
    final until = formatDisplayDate(period.reviewerAvailableUntil);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.infoSoft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            available ? Icons.groups_outlined : Icons.groups_2_outlined,
            color: AppColors.info,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Reviewer Availability',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                    color: AppColors.navy,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  available
                      ? 'Reviewers can conduct preparatory validation of submitted documentary requirements until $until.'
                      : 'Reviewer availability for this preparation cycle ended on $until.',
                  style: const TextStyle(
                    fontSize: 12,
                    height: 1.4,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
