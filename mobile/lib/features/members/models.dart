/// @file models.dart
/// @brief Public member profile model from `/users/{id}`.

/// @brief Public profile visible to other community members.
class MemberProfile {
  const MemberProfile({
    required this.id,
    required this.username,
    required this.displayName,
    this.avatarUrl,
    this.bio,
    this.title,
    this.pronouns,
    this.location,
    this.websiteUrl,
    this.role,
  });

  factory MemberProfile.fromJson(Map<String, dynamic> j) => MemberProfile(
        id: j['id'].toString(),
        username: j['username'] as String,
        displayName: j['display_name'] as String,
        avatarUrl: j['avatar_url'] as String?,
        bio: j['bio'] as String?,
        title: j['title'] as String?,
        pronouns: j['pronouns'] as String?,
        location: j['location'] as String?,
        websiteUrl: j['website_url'] as String?,
        role: j['role'] as String?,
      );

  final String id, username, displayName;
  final String? avatarUrl, bio, title, pronouns, location, websiteUrl, role;
}
