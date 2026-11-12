/// @file post_composer_screen.dart
/// @brief Compose a post: Markdown text (community visibility; media/visibility pending backend support).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/feed_provider.dart';

class PostComposerScreen extends ConsumerStatefulWidget {
  const PostComposerScreen({super.key});
  @override
  ConsumerState<PostComposerScreen> createState() => _PostComposerScreenState();
}

class _PostComposerScreenState extends ConsumerState<PostComposerScreen> {
  final _text = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_text.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await ref.read(createPostProvider)(_text.text.trim());
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not post.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('New post'), actions: [
          TextButton(onPressed: _busy ? null : _submit, child: const Text('Post')),
        ]),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          TextField(
            controller: _text,
            minLines: 5,
            maxLines: 12,
            decoration: const InputDecoration(
                labelText: 'What is happening?', helperText: 'Markdown supported', border: OutlineInputBorder()),
          ),
        ]),
      );
}
