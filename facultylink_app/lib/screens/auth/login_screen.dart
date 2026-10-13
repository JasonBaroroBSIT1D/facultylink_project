import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../navigation/app_routes.dart';
import '../../services/api_client.dart';
import '../../theme/app_colors.dart';
import '../../widgets/academic_auth_layout.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/app_text_field.dart';
import '../../widgets/dialogs.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController(text: 'maria.santos@university.edu.ph');
  final _password = TextEditingController(text: 'password123');
  bool _obscure = true;
  bool _loading = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await AppState.instance.login(_email.text, _password.text);
      if (!mounted) return;
      Navigator.pushNamedAndRemoveUntil(context, AppRoutes.main, (_) => false);
    } on ApiException catch (error) {
      if (!mounted) return;
      showAppSnackBar(context, error.message, error: true);
    } catch (_) {
      if (!mounted) return;
      showAppSnackBar(
        context,
        'Cannot reach the FacultyLink API. Keep Flask running and use the same Wi‑Fi as the computer.',
        error: true,
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AcademicAuthScaffold(
      onBack: () {
        if (Navigator.canPop(context)) {
          Navigator.pop(context);
        } else {
          Navigator.pushReplacementNamed(context, AppRoutes.welcome);
        }
      },
      form: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(28, 40, 28, 24),
          children: [
            const Text(
              'Sign in',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.navy,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Welcome back. Use your faculty email to continue preparing your documents.',
              style: TextStyle(
                color: AppColors.textSecondary,
                height: 1.4,
                fontSize: 14,
              ),
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
                if (value == null || value.trim().isEmpty) {
                  return 'Enter your faculty email';
                }
                if (!value.contains('@')) return 'Enter a valid email address';
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
              textInputAction: TextInputAction.done,
              suffix: IconButton(
                tooltip: _obscure ? 'Show password' : 'Hide password',
                onPressed: () => setState(() => _obscure = !_obscure),
                icon: Icon(
                  _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                  color: AppColors.textSecondary,
                ),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) return 'Enter your password';
                return null;
              },
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () {
                  Navigator.pushNamed(context, AppRoutes.forgotPassword);
                },
                child: const Text('Forgot password?'),
              ),
            ),
            const SizedBox(height: 8),
            PrimaryButton(
              label: 'Sign in',
              loading: _loading,
              onPressed: _login,
            ),
            const SizedBox(height: 18),
            const AuthOrDivider(),
            const SizedBox(height: 18),
            SecondaryButton(
              label: 'Sign up',
              onPressed: () {
                Navigator.pushNamed(context, AppRoutes.signUp);
              },
            ),
          ],
        ),
      ),
    );
  }
}

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    await Future<void>.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() => _loading = false);
    await showSuccessDialog(
      context: context,
      title: 'Reset link sent',
      message:
          'If this email is registered, a password reset link will be sent. This is a UI preview only.',
    );
    if (mounted) Navigator.pop(context);
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
              'Forgot password',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.navy,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Enter the email associated with your faculty account.',
              style: TextStyle(color: AppColors.textSecondary, height: 1.4),
            ),
            const SizedBox(height: 20),
            AppTextField(
              label: 'Email',
              controller: _email,
              underline: true,
              keyboardType: TextInputType.emailAddress,
              prefixIcon: Icons.mail_outline_rounded,
              validator: (value) {
                if (value == null || value.trim().isEmpty) return 'Enter your email';
                return null;
              },
            ),
            const SizedBox(height: 28),
            PrimaryButton(
              label: 'Send reset link',
              loading: _loading,
              onPressed: _submit,
            ),
            const SizedBox(height: 18),
            const AuthOrDivider(),
            const SizedBox(height: 18),
            SecondaryButton(
              label: 'Sign in',
              onPressed: () => Navigator.pop(context),
            ),
          ],
        ),
      ),
    );
  }
}
