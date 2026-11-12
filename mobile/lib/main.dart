/// @file main.dart
/// @brief App entry point (Material 3, Riverpod) with bottom navigation.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'features/chat/screens/chat_screen.dart';
import 'features/events/screens/calendar_screen.dart';
import 'features/feed/screens/feed_screen.dart';

void main() => runApp(const ProviderScope(child: NexaraApp()));

class NexaraApp extends StatelessWidget {
  const NexaraApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
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
