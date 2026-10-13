import 'package:flutter/material.dart';

import '../../data/app_state.dart';
import '../../models/enums.dart';
import '../../models/models.dart';
import '../../navigation/app_routes.dart';
import '../../theme/app_colors.dart';
import '../../widgets/app_buttons.dart';
import '../../widgets/common.dart';
import '../../widgets/document_card.dart';
import '../../widgets/preparation_period_card.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  final _search = TextEditingController();
  KraType? _kraFilter;
  DocumentStatus? _statusFilter;
  bool _loading = true;
  bool _error = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = false;
    });
    await Future<void>.delayed(const Duration(milliseconds: 700));
    if (!mounted) return;
    setState(() => _loading = false);
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<FacultyDocument> _filtered(List<FacultyDocument> source) {
    final query = _search.text.trim().toLowerCase();
    return source.where((doc) {
      final matchesQuery = query.isEmpty ||
          doc.title.toLowerCase().contains(query) ||
          doc.category.label.toLowerCase().contains(query);
      final matchesKra = _kraFilter == null || doc.kra == _kraFilter;
      final matchesStatus = _statusFilter == null || doc.status == _statusFilter;
      return matchesQuery && matchesKra && matchesStatus;
    }).toList();
  }

  Future<void> _openFilters() async {
    KraType? kra = _kraFilter;
    DocumentStatus? status = _statusFilter;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModal) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                20,
                12,
                20,
                20 + MediaQuery.paddingOf(context).bottom,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: AppColors.border,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Filter documents',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 16),
                  const Text('Key Result Area', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('All KRAs'),
                        selected: kra == null,
                        onSelected: (_) => setModal(() => kra = null),
                      ),
                      for (final type in KraType.values)
                        ChoiceChip(
                          label: Text(type.shortLabel),
                          selected: kra == type,
                          onSelected: (_) => setModal(() => kra = type),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Status', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('All statuses'),
                        selected: status == null,
                        onSelected: (_) => setModal(() => status = null),
                      ),
                      for (final value in DocumentStatus.values)
                        ChoiceChip(
                          label: Text(value.label),
                          selected: status == value,
                          onSelected: (_) => setModal(() => status = value),
                        ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  PrimaryButton(
                    label: 'Apply filters',
                    onPressed: () {
                      setState(() {
                        _kraFilter = kra;
                        _statusFilter = status;
                      });
                      Navigator.pop(context);
                    },
                  ),
                  const SizedBox(height: 8),
                  SecondaryButton(
                    label: 'Clear filters',
                    onPressed: () {
                      setState(() {
                        _kraFilter = null;
                        _statusFilter = null;
                      });
                      Navigator.pop(context);
                    },
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.instance,
      builder: (context, _) {
        final docs = _filtered(AppState.instance.documents);
        final hasActiveFilter =
            _kraFilter != null || _statusFilter != null || _search.text.isNotEmpty;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Documents'),
            actions: [
              IconButton(
                tooltip: 'Filter',
                onPressed: _openFilters,
                icon: Badge(
                  isLabelVisible: _kraFilter != null || _statusFilter != null,
                  child: const Icon(Icons.filter_list_rounded),
                ),
              ),
            ],
          ),
          floatingActionButton: FloatingActionButton.extended(
            backgroundColor: AppColors.navy,
            foregroundColor: Colors.white,
            onPressed: () {
              Navigator.pushNamed(context, AppRoutes.uploadDocument);
            },
            icon: const Icon(Icons.add),
            label: const Text('Add document'),
          ),
          body: _error
              ? ErrorState(
                  message:
                      'Documents could not be loaded. This is a simulated error state.',
                  onRetry: _load,
                )
              : CustomScrollView(
                  slivers: [
                    const SliverPadding(
                      padding: EdgeInsets.fromLTRB(16, 12, 16, 8),
                      sliver: SliverToBoxAdapter(
                        child: PreparationPeriodCard(),
                      ),
                    ),
                    if (_loading)
                      const SliverFillRemaining(
                        hasScrollBody: false,
                        child: LoadingState(message: 'Loading your documents…'),
                      )
                    else ...[
                      SliverPadding(
                        padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                        sliver: SliverToBoxAdapter(
                          child: TextField(
                            controller: _search,
                            onChanged: (_) => setState(() {}),
                            decoration: InputDecoration(
                              hintText: 'Search documents',
                              prefixIcon: const Icon(Icons.search_rounded),
                              suffixIcon: _search.text.isEmpty
                                  ? null
                                  : IconButton(
                                      onPressed: () {
                                        _search.clear();
                                        setState(() {});
                                      },
                                      icon: const Icon(Icons.close_rounded),
                                    ),
                            ),
                          ),
                        ),
                      ),
                      if (hasActiveFilter)
                        SliverPadding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                          sliver: SliverToBoxAdapter(
                            child: Text(
                              '${docs.length} result${docs.length == 1 ? '' : 's'}',
                              style: const TextStyle(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      if (docs.isEmpty)
                        SliverFillRemaining(
                          hasScrollBody: false,
                          child: EmptyState(
                            icon: Icons.folder_off_outlined,
                            title: hasActiveFilter
                                ? 'No matching documents'
                                : 'No documents uploaded',
                            message: hasActiveFilter
                                ? 'Try another search or clear your filters.'
                                : 'Upload teaching records, publications, certificates, and community service evidence to begin.',
                            actionLabel: hasActiveFilter
                                ? 'Clear filters'
                                : 'Upload document',
                            onAction: hasActiveFilter
                                ? () {
                                    setState(() {
                                      _search.clear();
                                      _kraFilter = null;
                                      _statusFilter = null;
                                    });
                                  }
                                : () {
                                    Navigator.pushNamed(
                                      context,
                                      AppRoutes.uploadDocument,
                                    );
                                  },
                          ),
                        )
                      else
                        SliverPadding(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
                          sliver: SliverList.separated(
                            itemCount: docs.length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final doc = docs[index];
                              return DocumentCard(
                                document: doc,
                                onTap: () {
                                  Navigator.pushNamed(
                                    context,
                                    AppRoutes.documentDetails,
                                    arguments: doc.id,
                                  );
                                },
                              );
                            },
                          ),
                        ),
                    ],
                  ],
                ),
        );
      },
    );
  }
}
