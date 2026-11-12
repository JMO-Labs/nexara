/// @file calendar_screen.dart
/// @brief Month/week calendar: pick a date, see that day's events.
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

enum _View { month, week }

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  late DateTime _selected = _day(widget.today ?? DateTime.now());
  _View _view = _View.month;
  static DateTime _day(DateTime d) => DateTime(d.year, d.month, d.day);

  /// @brief Monday of the week containing [d] (calendar arithmetic, DST-safe).
  static DateTime _weekStart(DateTime d) => DateTime(d.year, d.month, d.day - (d.weekday - 1));

  void _shiftWeek(int weeks) =>
      setState(() => _selected = DateTime(_selected.year, _selected.month, _selected.day + 7 * weeks));

  DateRange get _range {
    if (_view == _View.week) {
      final s = _weekStart(_selected);
      return (s, DateTime(s.year, s.month, s.day + 7));
    }
    return (DateTime(_selected.year, _selected.month), DateTime(_selected.year, _selected.month + 1));
  }

  Widget _weekStrip() {
    final start = _weekStart(_selected);
    return Row(children: [
      IconButton(tooltip: 'Previous week', icon: const Icon(Icons.chevron_left), onPressed: () => _shiftWeek(-1)),
      for (var i = 0; i < 7; i++) Expanded(child: _dayButton(DateTime(start.year, start.month, start.day + i))),
      IconButton(tooltip: 'Next week', icon: const Icon(Icons.chevron_right), onPressed: () => _shiftWeek(1)),
    ]);
  }

  Widget _dayButton(DateTime d) {
    final label = Text('${DateFormat.E().format(d)}\n${d.day}', textAlign: TextAlign.center);
    void tap() => setState(() => _selected = d);
    final semantic = DateFormat.yMMMEd().format(d);
    return Semantics(
      label: semantic,
      selected: d == _selected,
      excludeSemantics: true,
      button: true,
      child: d == _selected
          ? FilledButton.tonal(
              onPressed: tap,
              style: FilledButton.styleFrom(minimumSize: const Size(0, 52), padding: EdgeInsets.zero),
              child: label)
          : TextButton(
              onPressed: tap,
              style: TextButton.styleFrom(minimumSize: const Size(0, 52), padding: EdgeInsets.zero),
              child: label),
    );
  }

  @override
  Widget build(BuildContext context) {
    final range = _range;
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
        Padding(
          padding: const EdgeInsets.all(8),
          child: SegmentedButton<_View>(
            segments: const [
              ButtonSegment(value: _View.month, label: Text('Month'), icon: Icon(Icons.calendar_view_month)),
              ButtonSegment(value: _View.week, label: Text('Week'), icon: Icon(Icons.calendar_view_week)),
            ],
            selected: {_view},
            onSelectionChanged: (v) => setState(() => _view = v.first),
          ),
        ),
        if (_view == _View.month)
          CalendarDatePicker(
            key: ValueKey(_selected),
            initialDate: _selected,
            firstDate: DateTime(2000),
            lastDate: DateTime(2100),
            onDateChanged: (d) => setState(() => _selected = _day(d)),
          )
        else
          _weekStrip(),
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
