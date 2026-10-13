import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class ProgressRing extends StatelessWidget {
  const ProgressRing({
    super.key,
    required this.progress,
    this.size = 88,
    this.strokeWidth = 8,
    this.color = AppColors.gold,
    this.backgroundColor = const Color(0xFF234E73),
    this.child,
  });

  final double progress;
  final double size;
  final double strokeWidth;
  final Color color;
  final Color backgroundColor;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: 1,
            strokeWidth: strokeWidth,
            color: backgroundColor,
          ),
          CircularProgressIndicator(
            value: progress.clamp(0, 1),
            strokeWidth: strokeWidth,
            color: color,
            strokeCap: StrokeCap.round,
          ),
          ?child,
        ],
      ),
    );
  }
}

class LinearProgressLabeled extends StatelessWidget {
  const LinearProgressLabeled({
    super.key,
    required this.progress,
    this.color = AppColors.navy,
    this.height = 8,
  });

  final double progress;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(height),
      child: LinearProgressIndicator(
        value: progress.clamp(0, 1),
        minHeight: height,
        color: color,
        backgroundColor: color.withValues(alpha: 0.12),
      ),
    );
  }
}
