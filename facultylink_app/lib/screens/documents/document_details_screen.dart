import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../models/models.dart';
import '../../navigation/app_routes.dart';
import '../../theme/app_colors.dart';
import '../../utils/formatters.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/common.dart';
import '../../widgets/dialogs.dart';
import '../../widgets/status_badge.dart';

class DocumentDetailsScreen extends StatelessWidget {
  const DocumentDetailsScreen({super.key, required this.documentId});

  final String documentId;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.instance,
      builder: (context, _) {
        final document = AppState.instance.documentById(documentId);
        if (document == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Document')),
            body: const ErrorState(
              message: 'This document is no longer available.',
            ),
          );
        }
        return _DocumentDetailsBody(document: document);
      },
    );
  }
}

class _DocumentDetailsBody extends StatelessWidget {
  const _DocumentDetailsBody({required this.document});

  final FacultyDocument document;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Document details')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          Row(
            children: [
              Flexible(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: StatusBadge(status: document.status),
                ),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  document.points > 0 ? '${document.points} points' : 'No points yet',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    color: AppColors.navy,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            document.title,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              height: 1.25,
            ),
          ),
          const SizedBox(height: 16),
          _InfoRow(label: 'Document type', value: document.category.label),
          _InfoRow(label: 'KRA', value: document.kra.label),
          _InfoRow(label: 'Submission date', value: formatDisplayDate(document.submittedAt)),
          if (document.author != null)
            _InfoRow(label: 'Author / contributor', value: document.author!),
          _InfoRow(label: 'File', value: document.fileName),
          if (document.requiresAction) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.errorSoft,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.error.withValues(alpha: 0.25)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.priority_high_rounded, color: AppColors.error),
                      SizedBox(width: 8),
                      Text(
                        'Action required',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          color: AppColors.error,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    document.reviewerFeedback ??
                        'This document needs revision before it can be validated.',
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ] else if (document.reviewerFeedback != null) ...[
            const SizedBox(height: 16),
            const SectionHeader(title: 'Reviewer feedback'),
            InfoBanner(
              message: document.reviewerFeedback!,
              icon: Icons.chat_bubble_outline_rounded,
              color: AppColors.navy,
              background: AppColors.infoSoft,
            ),
          ],
          const SizedBox(height: 18),
          const SectionHeader(title: 'Validation result'),
          Text(
            document.validationResult ?? 'No validation result yet.',
            style: const TextStyle(color: AppColors.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 18),
          const SectionHeader(title: 'Extracted information'),
          const InfoBanner(
            message:
                'Extracted fields are placeholders. OCR and automated reading are not implemented yet.',
          ),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  if (document.extractedInfo.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(12),
                      child: Text(
                        'No extracted information is available for this file yet.',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    )
                  else
                    for (final entry in document.extractedInfo.entries)
                      _InfoRow(label: entry.key, value: entry.value),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          PrimaryButton(
            label: 'View file',
            icon: Icons.visibility_outlined,
            onPressed: () {
              showAppSnackBar(
                context,
                'File preview is simulated. ${document.fileName}',
              );
            },
          ),
          const SizedBox(height: 8),
          SecondaryButton(
            label: 'Download',
            icon: Icons.download_outlined,
            onPressed: () {
              showAppSnackBar(context, 'Download is simulated in this prototype.');
            },
          ),
          if (document.canResubmit) ...[
            const SizedBox(height: 8),
            PrimaryButton(
              label: 'Edit / resubmit',
              icon: Icons.upload_file_outlined,
              onPressed: () {
                Navigator.pushNamed(
                  context,
                  AppRoutes.uploadDocument,
                  arguments: document.kra,
                );
              },
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textTertiary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
