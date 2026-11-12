/// @file calendar_screen_test.dart
/// @brief Calendar lists events for the selected day; detail shows RSVP controls.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nexara_mobile/core/providers.dart';
import 'package:nexara_mobile/features/events/models/event_model.dart';
import 'package:nexara_mobile/features/events/providers/event_provider.dart';
import 'package:nexara_mobile/features/events/screens/calendar_screen.dart';

import '../../helpers/fake_realtime.dart';

final day = DateTime(2026, 3, 10, 18);

CalEvent ev({String? rsvp}) => CalEvent(
    id: 'e1', title: 'Picnic', startsAt: day, endsAt: day.add(const Duration(hours: 2)), location: 'Park', userRsvp: rsvp);

class FakeEventRepo implements EventRepository {
  String? rsvpStatus;
  @override
  Future<List<CalEvent>> inRange(DateTime start, DateTime end) async => [ev()];
  @override
  Future<CalEvent> detail(String id) async => ev(rsvp: rsvpStatus);
  @override
  Future<List<Attendee>> attendees(String id) async => [const Attendee('u1', 'attending')];
  @override
  Future<void> rsvp(String id, String status) async => rsvpStatus = status;
  @override
  Future<void> create({required String title, String? description, String? location, required DateTime start, required DateTime end, required String visibility}) async {}
}

void main() {
  Future<FakeEventRepo> pump(WidgetTester t) async {
    final repo = FakeEventRepo();
    await t.pumpWidget(ProviderScope(
      overrides: [eventRepositoryProvider.overrideWithValue(repo), realtimeClientProvider.overrideWithValue(FakeRealtime())],
      child: MaterialApp(home: CalendarScreen(today: day)),
    ));
    await t.pumpAndSettle();
    return repo;
  }

  testWidgets('calendar loads events for selected day', (t) async {
    await pump(t);
    expect(find.text('Picnic'), findsOneWidget);
  });

  testWidgets('event detail shows RSVP controls and RSVP updates', (t) async {
    final repo = await pump(t);
    await t.tap(find.text('Picnic'));
    await t.pumpAndSettle();
    expect(find.text('Going'), findsOneWidget);
    expect(find.text('Maybe'), findsOneWidget);
    await t.tap(find.text('Going'));
    await t.pumpAndSettle();
    expect(repo.rsvpStatus, 'attending');
    expect(tester(t, 'Going').selected, isTrue);
  });
}

ChoiceChip tester(WidgetTester t, String label) =>
    t.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, label));
