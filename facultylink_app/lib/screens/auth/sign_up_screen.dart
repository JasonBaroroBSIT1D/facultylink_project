import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../navigation/app_routes.dart';
import '../../services/api_client.dart';
import '../../theme/app_colors.dart';
import '../../widgets/academic_auth_layout.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/app_text_field.dart';
import '../../widgets/dialogs.dart';

class SignUpScreen extends StatefulWidget {
  const SignUpScreen({super.key});

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _loading = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final message = await AppState.instance.requestAccount(
        fullName: _name.text.trim(),
        email: _email.text.trim(),
      );
      if (!mounted) return;
      await showSuccessDialog(
        context: context,
        title: 'Request received',
        message: message,
      );
      if (mounted) Navigator.pop(context);
    } on ApiException catch (error) {
      if (!mounted) return;
      showAppSnackBar(context, error.message, error: true);
    } catch (_) {
      if (!mounted) return;
      showAppSnackBar(
        context,
        'Cannot reach the FacultyLink API. Start the Flask server on port 5000.',
        error: true,
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AcademicAuthScaffold(
      onBack: () => Navigator.pop(context),
      form: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(28, 40, 28, 24),
          children: [
            const Text(
              'Create account',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.navy,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Create a faculty account to start organizing your documentary evidence.',
              style: TextStyle(
                color: AppColors.textSecondary,
                height: 1.4,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 18),
            AppTextField(
              label: 'Name',
              controller: _name,
              underline: true,
              prefixIcon: Icons.person_outline_rounded,
              textInputAction: TextInputAction.next,
              validator: (value) =>
                  value == null || value.trim().isEmpty ? 'Enter your name' : null,
            ),
            const SizedBox(height: 18),
            AppTextField(
              label: 'Email',
              controller: _email,
              underline: true,
              keyboardType: TextInputType.emailAddress,
              prefixIcon: Icons.mail_outline_rounded,
              textInputAction: TextInputAction.next,
              validator: (value) {
                if (value == null || value.trim().isEmpty) return 'Enter your email';
                if (!value.contains('@')) return 'Enter a valid email';
                return null;
              },
            ),
            const SizedBox(height: 18),
            AppTextField(
              label: 'Password',
              controller: _password,
              underline: true,
              obscureText: _obscure,
              prefixIcon: Icons.lock_outline_rounded,
              suffix: IconButton(
                onPressed: () => setState(() => _obscure = !_obscure),
                icon: Icon(
                  _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                  color: AppColors.textSecondary,
                ),
              ),
              validator: (value) {
                if (value == null || value.length < 8) {
                  return 'Use at least 8 characters';
                }
                return null;
              },
            ),
            const SizedBox(height: 28),
            PrimaryButton(
              label: 'Sign up',
              loading: _loading,
              onPressed: _submit,
            ),
            const SizedBox(height: 18),
            const AuthOrDivider(),
            const SizedBox(height: 18),
            SecondaryButton(
              label: 'Sign in',
              onPressed: () {
                Navigator.pushReplacementNamed(context, AppRoutes.login);
              },
            ),
          ],
        ),
      ),
    );
  }
}
