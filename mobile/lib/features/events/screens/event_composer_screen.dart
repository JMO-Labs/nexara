/// @file event_composer_screen.dart
/// @brief Create an event: title, description, date/time, location, visibility.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../providers/event_provider.dart';

class EventComposerScreen extends ConsumerStatefulWidget {
  const EventComposerScreen({super.key});
  @override
  ConsumerState<EventComposerScreen> createState() => _EventComposerScreenState();
}

class _EventComposerScreenState extends ConsumerState<EventComposerScreen> {
  final _title = TextEditingController();
  final _desc = TextEditingController();
  final _loc = TextEditingController();
  DateTime _start = DateTime.now().add(const Duration(hours: 1));
  String _visibility = 'community';
  bool _busy = false;

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    _loc.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final d = await showDatePicker(
        context: context, initialDate: _start, firstDate: DateTime(2000), lastDate: DateTime(2100));
    if (d == null || !mounted) return;
    final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_start));
    if (t == null) return;
    setState(() => _start = DateTime(d.year, d.month, d.day, t.hour, t.minute));
  }

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await ref.read(eventRepositoryProvider).create(
          title: _title.text.trim(),
          description: _desc.text.trim(),
          location: _loc.text.trim(),
          start: _start,
          end: _start.add(const Duration(hours: 1)),
          visibility: _visibility);
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not create event.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('New event'), actions: [
          TextButton(onPressed: _busy ? null : _submit, child: const Text('Create')),
        ]),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          TextField(controller: _title, decoration: const InputDecoration(labelText: 'Title', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(
              controller: _desc,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _loc, decoration: const InputDecoration(labelText: 'Location', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          ListTile(
            leading: const Icon(Icons.schedule),
            title: Text(DateFormat.yMMMEd().add_jm().format(_start)),
            subtitle: const Text('Starts (duration 1 hour)'),
            onTap: _pick,
          ),
          DropdownButtonFormField<String>(
            value: _visibility,
            decoration: const InputDecoration(labelText: 'Visibility', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'community', child: Text('Community')),
              DropdownMenuItem(value: 'subgroup', child: Text('Subgroup')),
              DropdownMenuItem(value: 'private', child: Text('Private')),
            ],
            onChanged: (v) => setState(() => _visibility = v ?? 'community'),
          ),
        ]),
      );
}
