/// @file main.dart
/// @brief App entry point (Material 3, Riverpod) with bottom navigation.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/offline/connectivity_service.dart';
import 'features/chat/screens/chat_screen.dart';
import 'features/chat/screens/conversation_screen.dart';
import 'features/events/screens/event_detail_screen.dart';
import 'features/feed/screens/post_detail_screen.dart';
import 'features/notifications/handlers/push_handler.dart';
import 'features/notifications/providers/push_provider.dart';
import 'features/events/screens/calendar_screen.dart';
import 'features/feed/screens/feed_screen.dart';

void main() => runApp(const ProviderScope(child: NexaraApp()));

final navigatorKey = GlobalKey<NavigatorState>();

/// @brief Map a deep-link route (see routeForPayload) to a screen.
Route<dynamic>? onGenerateRoute(RouteSettings r) {
  final seg = Uri.parse(r.name ?? '/').pathSegments;
  if (seg.length != 2) return null;
  final Widget? w = switch (seg[0]) {
    'posts' => PostDetailScreen(postId: seg[1]),
    'chat' => ConversationScreen(chatId: seg[1], title: 'Chat'),
    'events' => EventDetailScreen(eventId: seg[1]),
    _ => null,
  };
  return w == null ? null : MaterialPageRoute<void>(builder: (_) => w, settings: r);
}

class NexaraApp extends ConsumerStatefulWidget {
  const NexaraApp({super.key});
  @override
  ConsumerState<NexaraApp> createState() => _NexaraAppState();
}

class _NexaraAppState extends ConsumerState<NexaraApp> {
  PushHandler? _push;

  @override
  void initState() {
    super.initState();
    // Push needs a configured Firebase project; fail soft when absent.
    Future<void>(() async {
      try {
        final svc = ref.read(pushServiceProvider);
        await svc.init();
        _push = PushHandler(
            service: svc, navigate: (r) => navigatorKey.currentState?.pushNamed(r))
          ..start();
      } catch (_) {}
    });
  }

  @override
  void dispose() {
    _push?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        navigatorKey: navigatorKey,
        onGenerateRoute: onGenerateRoute,
        builder: (context, child) => Column(children: [
          const SafeArea(bottom: false, child: OfflineBanner()),
          Expanded(child: child ?? const SizedBox.shrink()),
        ]),
        title: 'Nexara',
        theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
        darkTheme: ThemeData(
            useMaterial3: true, colorSchemeSeed: Colors.indigo, brightness: Brightness.dark),
        home: const HomeShell(),
      );
}

/// @brief Tabbed shell: Feed, Chat, Calendar.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _i = 0;
  static const _pages = [FeedScreen(), ChatScreen(), CalendarScreen()];

  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: _i, children: _pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _i,
          onDestinationSelected: (i) => setState(() => _i = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dynamic_feed), label: 'Feed'),
            NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Chat'),
            NavigationDestination(icon: Icon(Icons.calendar_month), label: 'Calendar'),
          ],
        ),
      );
}
