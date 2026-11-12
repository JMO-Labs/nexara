/// @file event_model.dart
/// @brief Calendar event and RSVP models.
class CalEvent {
  const CalEvent({
    required this.id,
    required this.title,
    required this.startsAt,
    required this.endsAt,
    this.description,
    this.location,
    this.rsvpCounts = const {},
    this.userRsvp,
  });
  factory CalEvent.fromJson(Map<String, dynamic> j) => CalEvent(
        id: j['id'].toString(),
        title: (j['title'] ?? '').toString(),
        description: j['description'] as String?,
        location: j['location'] as String?,
        startsAt: DateTime.parse(j['starts_at'].toString()).toLocal(),
        endsAt: DateTime.parse(j['ends_at'].toString()).toLocal(),
        rsvpCounts: ((j['rsvp_counts'] as Map?) ?? const {})
            .map((k, v) => MapEntry(k.toString(), (v as num).toInt())),
        userRsvp: (j['user_rsvp'] as Map?)?['status']?.toString(),
      );
  final String id;
  final String title;
  final String? description;
  final String? location;
  final DateTime startsAt;
  final DateTime endsAt;
  final Map<String, int> rsvpCounts;
  final String? userRsvp;
}

class Attendee {
  const Attendee(this.userId, this.status);
  factory Attendee.fromJson(Map<String, dynamic> j) =>
      Attendee(j['user_id'].toString(), j['status'].toString());
  final String userId;
  final String status;
}
