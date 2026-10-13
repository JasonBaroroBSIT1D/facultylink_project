import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../data/app_state.dart';
import '../../models/enums.dart';
import '../../services/api_client.dart';
import '../../theme/app_colors.dart';
import '../../utils/formatters.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/app_text_field.dart';
import '../../widgets/common.dart';
import '../../widgets/dialogs.dart';

class UploadDocumentScreen extends StatefulWidget {
  const UploadDocumentScreen({super.key, this.initialKra});

  final KraType? initialKra;

  @override
  State<UploadDocumentScreen> createState() => _UploadDocumentScreenState();
}

class _UploadDocumentScreenState extends State<UploadDocumentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _author = TextEditingController(text: 'Maria Santos');
  final _dateController = TextEditingController(text: formatDisplayDate(DateTime(2026, 8, 28)));
  DateTime _date = DateTime(2026, 8, 28);
  DocumentCategory? _category;
  KraType? _kra;
  String? _fileName;
  List<int>? _fileBytes;
  bool _fromCamera = false;
  _UploadPhase _phase = _UploadPhase.form;

  @override
  void initState() {
    super.initState();
    _kra = widget.initialKra;
  }

  @override
  void dispose() {
    _title.dispose();
    _author.dispose();
    _dateController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2018),
      lastDate: DateTime(2027),
    );
    if (picked != null) {
      setState(() {
        _date = picked;
        _dateController.text = formatDisplayDate(picked);
      });
    }
  }

  Future<void> _pickFile({required bool camera}) async {
    if (camera) {
      try {
        final shot = await ImagePicker().pickImage(
          source: ImageSource.camera,
          imageQuality: 85,
        );
        if (shot == null) return;
        final bytes = await shot.readAsBytes();
        if (!mounted) return;
        setState(() {
          _fromCamera = true;
          _fileName = shot.name.isNotEmpty
              ? shot.name
              : 'scan_${DateTime.now().millisecondsSinceEpoch}.jpg';
          _fileBytes = bytes;
        });
      } catch (_) {
        if (!mounted) return;
        showAppSnackBar(
          context,
          'Camera is unavailable. Allow camera permission, or choose a file instead.',
          error: true,
        );
      }
      return;
    }

    final result = await FilePicker.platform.pickFiles(withData: true);
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    setState(() {
      _fromCamera = false;
      _fileName = file.name;
      _fileBytes = file.bytes;
    });
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_fileName == null) {
      showAppSnackBar(context, 'Select or scan a file first.', error: true);
      return;
    }

    setState(() => _phase = _UploadPhase.processing);
    try {
      await AppState.instance.uploadDocument(
        title: _title.text.trim(),
        category: _category!,
        kra: _kra!,
        author: _author.text.trim(),
        fileName: _fileName!,
        fileBytes: _fileBytes,
      );
      if (!mounted) return;
      setState(() => _phase = _UploadPhase.success);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _phase = _UploadPhase.form);
      showAppSnackBar(context, error.message, error: true);
    } catch (_) {
      if (!mounted) return;
      setState(() => _phase = _UploadPhase.form);
      showAppSnackBar(
        context,
        'Upload failed. If you are signed in, confirm the Flask API is running.',
        error: true,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload document')),
      body: switch (_phase) {
        _UploadPhase.form => _buildForm(),
        _UploadPhase.processing => const LoadingState(
            message: 'Submitting your document…\nThe API will classify the KRA and queue it for reviewer validation.',
          ),
        _UploadPhase.success => _SuccessView(
            onDone: () => Navigator.pop(context),
            onUploadAnother: () {
              setState(() {
                _phase = _UploadPhase.form;
                _title.clear();
                _fileName = null;
                _fileBytes = null;
                _fromCamera = false;
              });
            },
          ),
      },
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          const InfoBanner(
            message:
                'Uploaded files are stored on the FacultyLink API. Keyword rules assign a KRA; reviewers confirm the score.',
          ),
          const SizedBox(height: 18),
          DropdownButtonFormField<DocumentCategory>(
            initialValue: _category,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Document type'),
            items: [
              for (final type in DocumentCategory.values)
                DropdownMenuItem(
                  value: type,
                  child: Text(type.label, overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: (value) => setState(() => _category = value),
            validator: (value) => value == null ? 'Select a document type' : null,
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<KraType>(
            initialValue: _kra,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Associated KRA'),
            items: [
              for (final type in KraType.values)
                DropdownMenuItem(
                  value: type,
                  child: Text(type.label, overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: (value) => setState(() => _kra = value),
            validator: (value) => value == null ? 'Select a KRA' : null,
          ),
          const SizedBox(height: 14),
          AppTextField(
            label: 'Document title',
            controller: _title,
            hint: 'Example: Course syllabus, SY 2025–2026',
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Enter a document title';
              }
              return null;
            },
          ),
          const SizedBox(height: 14),
          AppTextField(
            label: 'Date',
            readOnly: true,
            controller: _dateController,
            prefixIcon: Icons.event_outlined,
            onTap: _pickDate,
          ),
          const SizedBox(height: 14),
          AppTextField(
            label: 'Author / contributor',
            controller: _author,
            prefixIcon: Icons.person_outline_rounded,
          ),
          const SizedBox(height: 18),
          const Text(
            'File',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
          ),
          const SizedBox(height: 8),
          if (_fileName == null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  const Icon(Icons.cloud_upload_outlined, size: 36, color: AppColors.navy),
                  const SizedBox(height: 8),
                  const Text(
                    'Select a PDF, image, or scan a physical document.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 14),
                  SecondaryButton(
                    label: 'Choose file',
                    icon: Icons.attach_file_rounded,
                    onPressed: () => _pickFile(camera: false),
                  ),
                  const SizedBox(height: 8),
                  SecondaryButton(
                    label: 'Camera / scan',
                    icon: Icons.photo_camera_outlined,
                    onPressed: () => _pickFile(camera: true),
                  ),
                ],
              ),
            )
          else
            Card(
              child: ListTile(
                leading: Icon(
                  _fromCamera ? Icons.photo_outlined : Icons.picture_as_pdf_outlined,
                  color: AppColors.navy,
                ),
                title: Text(_fileName!, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(_fromCamera ? 'Captured image preview' : 'Selected file preview'),
                trailing: IconButton(
                  tooltip: 'Remove file',
                  onPressed: () => setState(() => _fileName = null),
                  icon: const Icon(Icons.close_rounded),
                ),
              ),
            ),
          if (_fileName != null) ...[
            const SizedBox(height: 8),
            SecondaryButton(
              label: 'Change file',
              icon: Icons.swap_horiz_rounded,
              onPressed: () => _pickFile(camera: false),
            ),
            const SizedBox(height: 8),
            SecondaryButton(
              label: 'Camera / scan',
              icon: Icons.photo_camera_outlined,
              onPressed: () => _pickFile(camera: true),
            ),
          ],
          const SizedBox(height: 24),
          PrimaryButton(
            label: 'Upload document',
            icon: Icons.cloud_upload_outlined,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}

enum _UploadPhase { form, processing, success }

class _SuccessView extends StatelessWidget {
  const _SuccessView({required this.onDone, required this.onUploadAnother});

  final VoidCallback onDone;
  final VoidCallback onUploadAnother;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 88,
            height: 88,
            decoration: const BoxDecoration(
              color: AppColors.successSoft,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check_rounded, color: AppColors.success, size: 48),
          ),
          const SizedBox(height: 20),
          const Text(
            'Document submitted',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Your file was submitted with a Pending Review status. Rule-based scoring ran on the server; a reviewer still confirms the result.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textSecondary, height: 1.45),
          ),
          const SizedBox(height: 28),
          PrimaryButton(label: 'Back to documents', onPressed: onDone),
          const SizedBox(height: 10),
          SecondaryButton(label: 'Upload another', onPressed: onUploadAnother),
        ],
      ),
    );
  }
}
