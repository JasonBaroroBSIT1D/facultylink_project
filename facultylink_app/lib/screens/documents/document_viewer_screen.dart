import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../models/models.dart';
import '../../services/api_client.dart';
import '../../theme/app_colors.dart';
import '../../utils/open_document_bytes.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/common.dart';
import '../../widgets/dialogs.dart';

class DocumentViewerScreen extends StatefulWidget {
  const DocumentViewerScreen({super.key, required this.document});

  final FacultyDocument document;

  @override
  State<DocumentViewerScreen> createState() => _DocumentViewerScreenState();
}

class _DocumentViewerScreenState extends State<DocumentViewerScreen> {
  bool _loading = true;
  String? _error;
  Uint8List? _bytes;
  String? _localPath;
  bool _openedExternally = false;

  bool get _isImage {
    final mime = (widget.document.mimeType ?? '').toLowerCase();
    final name = widget.document.fileName.toLowerCase();
    return mime.startsWith('image/') ||
        name.endsWith('.png') ||
        name.endsWith('.jpg') ||
        name.endsWith('.jpeg') ||
        name.endsWith('.webp') ||
        name.endsWith('.gif') ||
        name.endsWith('.bmp');
  }

  bool get _isPdf {
    final mime = (widget.document.mimeType ?? '').toLowerCase();
    final name = widget.document.fileName.toLowerCase();
    return mime.contains('pdf') || name.endsWith('.pdf');
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _openedExternally = false;
    });
    try {
      if (!AppState.instance.usingApi || !widget.document.hasFile) {
        throw ApiException('Original file is not available for this document.');
      }
      final bytes = Uint8List.fromList(
        await AppState.instance.api.downloadDocumentBytes(widget.document.id),
      );
      String? localPath;
      if (!kIsWeb) {
        localPath = await saveDocumentBytes(
          bytes,
          '${widget.document.id}_${widget.document.fileName}',
        );
      }
      if (!mounted) return;
      setState(() {
        _bytes = bytes;
        _localPath = localPath;
        _loading = false;
        _error = null;
      });
      if (!_isImage) {
        // Reached only after "View document" on the details screen.
        await _openExternal(auto: true);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = kIsWeb
            ? 'Could not open the file in Chrome. Confirm Flask is running on http://127.0.0.1:5000.'
            : 'Cannot reach the FacultyLink API from this phone. Keep Flask running and stay on the same Wi‑Fi as the computer.';
      });
    }
  }

  Future<void> _openExternal({bool auto = false}) async {
    if (_bytes == null) return;
    try {
      final opened = kIsWeb
          ? await openDocumentBytesInBrowser(
              _bytes!,
              fileName: widget.document.fileName,
              mimeType: widget.document.mimeType,
            )
          : (_localPath != null && await openSavedDocument(_localPath!));
      if (!mounted) return;
      if (opened) {
        setState(() => _openedExternally = true);
        return;
      }
      if (!auto) {
        showAppSnackBar(
          context,
          kIsWeb
              ? 'Browser blocked the file tab. Allow pop-ups for this site, then try again.'
              : 'No app on this device can open that file.',
          error: true,
        );
      } else if (!kIsWeb) {
        showAppSnackBar(
          context,
          'File downloaded. Tap Open again if no viewer opened.',
        );
      }
    } catch (_) {
      if (!mounted) return;
      if (!auto) {
        showAppSnackBar(
          context,
          kIsWeb
              ? 'Browser could not open that file.'
              : 'No app on this device can open that file.',
          error: true,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final doc = widget.document;
    return Scaffold(
      backgroundColor: _isImage && !_loading && _error == null ? Colors.black : null,
      appBar: AppBar(
        title: Text(doc.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (_bytes != null)
            IconButton(
              tooltip: kIsWeb ? 'Open in new tab' : 'Open in external app',
              onPressed: () => _openExternal(),
              icon: const Icon(Icons.open_in_new_rounded),
            ),
        ],
      ),
      body: _loading
          ? const LoadingState(message: 'Opening document…')
          : _error != null
              ? Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      SecondaryButton(label: 'Retry', onPressed: _load),
                    ],
                  ),
                )
              : _isImage && _bytes != null
                  ? InteractiveViewer(
                      minScale: 0.5,
                      maxScale: 5,
                      child: Center(child: Image.memory(_bytes!)),
                    )
                  : Center(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              _openedExternally
                                  ? Icons.check_circle_outline_rounded
                                  : (_isPdf
                                      ? Icons.picture_as_pdf_outlined
                                      : Icons.description_outlined),
                              size: 48,
                              color: AppColors.navy,
                            ),
                            const SizedBox(height: 14),
                            Text(
                              _openedExternally
                                  ? (kIsWeb
                                      ? 'Opened in a new browser tab'
                                      : 'Opened in your device viewer')
                                  : doc.fileName,
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              kIsWeb
                                  ? 'Chrome will show the PDF/document in a new tab. Allow pop-ups if nothing appears.'
                                  : 'Use the device viewer for pages, zoom, and full layout.',
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                color: AppColors.textSecondary,
                                height: 1.4,
                              ),
                            ),
                            const SizedBox(height: 20),
                            PrimaryButton(
                              label: kIsWeb ? 'Open in new tab' : 'Open again',
                              icon: Icons.visibility_outlined,
                              onPressed: () => _openExternal(),
                            ),
                          ],
                        ),
                      ),
                    ),
    );
  }
}
