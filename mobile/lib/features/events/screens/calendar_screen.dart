/// @file calendar_screen.dart
/// @brief Month calendar: pick a date, see that day's events.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../providers/event_provider.dart';
import 'event_composer_screen.dart';
import 'event_detail_screen.dart';

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key, this.today});
  final DateTime? today; // injectable for tests
  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  late DateTime _selected = _day(widget.today ?? DateTime.now());
  static DateTime _day(DateTime d) => DateTime(d.year, d.month, d.day);

  @override
  Widget build(BuildContext context) {
    final first = DateTime(_selected.year, _selected.month);
    final range = (first, DateTime(_selected.year, _selected.month + 1));
    final events = ref.watch(eventsInRangeProvider(range));
    return Scaffold(
      appBar: AppBar(title: Text(DateFormat.yMMMM().format(_selected))),
      floatingActionButton: FloatingActionButton(
        tooltip: 'New event',
        onPressed: () => Navigator.of(context)
            .push(MaterialPageRoute<void>(builder: (_) => const EventComposerScreen())),
        child: const Icon(Icons.add),
      ),
      body: Column(children: [
        CalendarDatePicker(
          initialDate: _selected,
          firstDate: DateTime(2000),
          lastDate: DateTime(2100),
          onDateChanged: (d) => setState(() => _selected = _day(d)),
        ),
        const Divider(height: 1),
        Expanded(
          child: events.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => const Center(child: Text('Could not load events.')),
            data: (list) {
              final day = list.where((e) => _day(e.startsAt) == _selected).toList()
                ..sort((a, b) => a.startsAt.compareTo(b.startsAt));
              if (day.isEmpty) return const Center(child: Text('No events this day'));
              return ListView(children: [
                for (final e in day)
                  ListTile(
                    leading: const Icon(Icons.event),
                    title: Text(e.title),
                    subtitle: Text(
                        '${DateFormat.jm().format(e.startsAt)}${e.location == null ? '' : ' · ${e.location}'}'),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => EventDetailScreen(eventId: e.id))),
                  ),
              ]);
            },
          ),
        ),
      ]),
    );
  }
}
