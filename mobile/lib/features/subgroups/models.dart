/// @file models.dart
/// @brief Subgroup and membership models (hand-written JSON parsing).

/// @brief Subgroup summary/detail from `/subgroups`.
class Subgroup {
  const Subgroup({
    required this.id,
    required this.name,
    required this.slug,
    this.description,
    this.avatarUrl,
    this.isPrivate = false,
    this.joinPolicy = 'open',
    this.myRole,
    this.memberCount,
  });

  factory Subgroup.fromJson(Map<String, dynamic> j) => Subgroup(
        id: j['id'].toString(),
        name: j['name'] as String,
        slug: j['slug'] as String,
        description: j['description'] as String?,
        avatarUrl: j['avatar_url'] as String?,
        isPrivate: j['is_private'] as bool? ?? false,
        joinPolicy: j['join_policy'] as String? ?? 'open',
        myRole: j['my_role'] as String?,
        memberCount: j['member_count'] as int?,
      );

  final String id, name, slug, joinPolicy;
  final String? description, avatarUrl, myRole;
  final bool isPrivate;
  final int? memberCount;
}

/// @brief Member row from `/subgroups/{slug}/members`.
class SubgroupMember {
  const SubgroupMember(
      {required this.userId, required this.role, this.username, this.displayName, this.avatarUrl});

  factory SubgroupMember.fromJson(Map<String, dynamic> j) => SubgroupMember(
        userId: j['user_id'].toString(),
        role: j['role'] as String,
        username: j['username'] as String?,
        displayName: j['display_name'] as String?,
        avatarUrl: j['avatar_url'] as String?,
      );

  final String userId, role;
  final String? username, displayName, avatarUrl;

  String get label => displayName ?? username ?? 'Unknown';
}
