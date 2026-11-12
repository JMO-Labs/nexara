/// @file event_detail_screen.dart
/// @brief Event info, RSVP controls and attendee list.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../providers/event_provider.dart';

const rsvpOptions = {'attending': 'Going', 'maybe': 'Maybe', 'declined': 'Can\'t go'};

class EventDetailScreen extends ConsumerWidget {
  const EventDetailScreen({super.key, required this.eventId});
  final String eventId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ev = ref.watch(eventDetailProvider(eventId));
    final att = ref.watch(attendeesProvider(eventId));
    return Scaffold(
      appBar: AppBar(title: const Text('Event')),
      body: ev.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(child: Text('Could not load the event.')),
        data: (e) => ListView(padding: const EdgeInsets.all(16), children: [
          Text(e.title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text('${DateFormat.yMMMEd().add_jm().format(e.startsAt)} – ${DateFormat.jm().format(e.endsAt)}'),
          if (e.location != null) Text(e.location!),
          if (e.description != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(e.description!)),
          const SizedBox(height: 16),
          Text('Your RSVP', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            for (final o in rsvpOptions.entries)
              ChoiceChip(
                label: Text(o.value),
                selected: e.userRsvp == o.key,
                onSelected: (_) => ref.read(rsvpProvider)(eventId, o.key),
              ),
          ]),
          const Divider(height: 32),
          Text('Attendees', style: Theme.of(context).textTheme.titleMedium),
          att.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const Text('Could not load attendees.'),
            data: (list) => Column(children: [
              for (final a in list)
                ListTile(
                    dense: true,
                    leading: const Icon(Icons.person),
                    title: Text(a.userId),
                    trailing: Text(rsvpOptions[a.status] ?? a.status)),
            ]),
          ),
        ]),
      ),
    );
  }
}
