/// @file main.dart
/// @brief App entry point (Material 3, Riverpod).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() => runApp(const ProviderScope(child: NexaraApp()));

class NexaraApp extends StatelessWidget {
  const NexaraApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Nexara',
        theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
        darkTheme: ThemeData(
            useMaterial3: true, colorSchemeSeed: Colors.indigo, brightness: Brightness.dark),
        home: const Scaffold(body: Center(child: Text('Nexara'))),
      );
}
