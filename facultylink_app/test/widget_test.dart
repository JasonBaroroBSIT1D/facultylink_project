import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:facultylink_app/main.dart';
import 'package:facultylink_app/navigation/main_shell.dart';
import 'package:facultylink_app/theme/app_theme.dart';

void main() {
  Future<void> setPhoneSize(WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
  }

  testWidgets('splash then welcome then sign in', (WidgetTester tester) async {
    await setPhoneSize(tester);
    await tester.pumpWidget(const FacultyLinkApp());

    expect(find.text('Self-assessment tool'), findsOneWidget);
    expect(find.text('Self Assessment'), findsWidgets);
    expect(
      find.text('Faculty Evaluation and Self-Assessment System'),
      findsWidgets,
    );

    await tester.pump(const Duration(milliseconds: 2300));
    await tester.pumpAndSettle();

    expect(find.text('HELLO'), findsNothing);
    expect(find.text('Get Started'), findsOneWidget);

    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in'), findsWidgets);
  });

  testWidgets('faculty shell tabs show mock faculty data', (WidgetTester tester) async {
    await setPhoneSize(tester);
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const MainShell(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Maria Santos'), findsWidgets);
    expect(find.text('Simulation Result'), findsOneWidget);
    expect(find.text('Eligible For'), findsOneWidget);
    expect(find.text('Readiness'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Evaluation Preparation Period'), findsOneWidget);
    expect(find.text('Closing Soon'), findsOneWidget);
    expect(
      find.textContaining('FacultyLink is a preparatory and self-assessment platform'),
      findsOneWidget,
    );

    await tester.tap(find.byIcon(Icons.description_outlined));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 800));
    expect(find.text('Add document'), findsOneWidget);
    expect(find.text('Evaluation Preparation Period'), findsWidgets);
    expect(find.text('Closing Soon'), findsWidgets);

    await tester.tap(find.byIcon(Icons.track_changes_outlined));
    await tester.pumpAndSettle();
    expect(find.text('Instructor I'), findsWidgets);
    expect(find.text('Instructor II'), findsWidgets);
    expect(find.text('Simulation Result'), findsWidgets);
    expect(find.text('Readiness'), findsWidgets);

    await tester.tap(
      find.descendant(
        of: find.byType(NavigationBar),
        matching: find.text('Notifications'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Notifications'), findsWidgets);

    await tester.tap(find.text('Profile').hitTestable());
    await tester.pumpAndSettle();
    expect(find.text('FL-2024-0847'), findsOneWidget);
    await tester.fling(find.text('FL-2024-0847'), const Offset(0, -500), 1200);
    await tester.pumpAndSettle();
    expect(find.text('Edit profile'), findsOneWidget);
  });
}
