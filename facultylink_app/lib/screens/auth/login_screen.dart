import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../navigation/app_routes.dart';
import '../../services/api_client.dart';
import '../../widgets/auth_ui.dart';
import '../../widgets/dialogs.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, this.initialEmail});

  /// Pre-filled after a successful password reset.
  final String? initialEmail;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _email =
      TextEditingController(text: widget.initialEmail ?? '');
  final _password = TextEditingController();
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
    return AuthBackdrop(
      child: AuthCard(
        badgeIcon: Icons.lock_open_rounded,
        children: [
          const AuthHeading(
            eyebrow: 'FACULTYLINK',
            title: 'Login here',
            subtitle: 'Welcome back! Sign in with your faculty\nemail to continue.',
          ),
          Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AuthField(
                  hint: 'Email',
                  controller: _email,
                  prefixIcon: Icons.mail_outline_rounded,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autofillHints: const [AutofillHints.username, AutofillHints.email],
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Enter your faculty email';
                    }
                    if (!value.contains('@')) return 'Enter a valid email address';
                    return null;
                  },
                ),
                const SizedBox(height: 2),
                AuthField(
                  hint: 'Password',
                  controller: _password,
                  prefixIcon: Icons.lock_outline_rounded,
                  obscureText: _obscure,
                  textInputAction: TextInputAction.done,
                  autofillHints: const [AutofillHints.password],
                  onSubmitted: (_) => _loading ? null : _login(),
                  suffix: IconButton(
                    tooltip: _obscure ? 'Show password' : 'Hide password',
                    onPressed: () => setState(() => _obscure = !_obscure),
                    icon: Icon(
                      _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                      color: AuthPalette.iconIdle,
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'Enter your password';
                    return null;
                  },
                ),
              ],
            ),
          ),
          AuthLink(
            label: 'Forgot your password?',
            color: AuthPalette.primary,
            fontSize: 13.5,
            alignment: Alignment.centerRight,
            onPressed: () => Navigator.pushNamed(
              context,
              AppRoutes.forgotPassword,
              arguments: _email.text.trim(),
            ),
          ),
          const SizedBox(height: 14),
          AuthButton(label: 'Sign in', loading: _loading, onPressed: _login),
        ],
      ),
    );
  }
}
