/// @file event_provider.dart
/// @brief Riverpod providers for events in a range, event detail, RSVP and creation.
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../models/event_model.dart';

class EventRepository {
  EventRepository(this._dio);
  final Dio _dio;

  Future<List<CalEvent>> inRange(DateTime start, DateTime end) async {
    final r = await _dio.get('/events', queryParameters: {
      'start': start.toUtc().toIso8601String(),
      'end': end.toUtc().toIso8601String(),
    });
    return [for (final e in (r.data as Map)['items'] as List) CalEvent.fromJson(e as Map<String, dynamic>)];
  }

  Future<CalEvent> detail(String id) async =>
      CalEvent.fromJson((await _dio.get('/events/$id')).data as Map<String, dynamic>);

  Future<List<Attendee>> attendees(String id) async {
    final r = await _dio.get('/events/$id/rsvps');
    return [for (final a in r.data as List) Attendee.fromJson(a as Map<String, dynamic>)];
  }

  Future<void> rsvp(String id, String status) =>
      _dio.post('/events/$id/rsvp', data: {'status': status});

  Future<void> create({
    required String title,
    String? description,
    String? location,
    required DateTime start,
    required DateTime end,
    required String visibility,
  }) =>
      _dio.post('/events', data: {
        'title': title,
        if (description != null && description.isNotEmpty) 'description': description,
        if (location != null && location.isNotEmpty) 'location': location,
        'starts_at': start.toUtc().toIso8601String(),
        'ends_at': end.toUtc().toIso8601String(),
        'visibility': visibility,
      });
}

final eventRepositoryProvider =
    Provider<EventRepository>((ref) => EventRepository(ref.watch(apiClientProvider).dio));

/// @brief Record key for family params (Dart records have value equality).
typedef DateRange = (DateTime start, DateTime end);

/// @brief Events in [start, end); refreshes on realtime event changes.
final eventsInRangeProvider = FutureProvider.family<List<CalEvent>, DateRange>((ref, range) {
  final sub = ref.watch(realtimeClientProvider).messages.listen((m) {
    if (m.type == 'event_update' || m.type == 'event.updated') ref.invalidateSelf();
  });
  ref.onDispose(sub.cancel);
  return ref.watch(eventRepositoryProvider).inRange(range.$1, range.$2);
});

final eventDetailProvider = FutureProvider.family<CalEvent, String>((ref, id) {
  final sub = ref.watch(realtimeClientProvider).messages.listen((m) {
    if ((m.type == 'event_update' || m.type == 'event.updated') && m.payload['event_id']?.toString() == id) {
      ref.invalidateSelf();
    }
  });
  ref.onDispose(sub.cancel);
  return ref.watch(eventRepositoryProvider).detail(id);
});

final attendeesProvider = FutureProvider.family<List<Attendee>, String>(
    (ref, id) => ref.watch(eventRepositoryProvider).attendees(id));

/// @brief Mutation: cast an RSVP then refresh the event and attendee list.
final rsvpProvider = Provider<Future<void> Function(String eventId, String status)>((ref) {
  return (id, status) async {
    await ref.read(eventRepositoryProvider).rsvp(id, status);
    ref.invalidate(eventDetailProvider(id));
    ref.invalidate(attendeesProvider(id));
  };
});
