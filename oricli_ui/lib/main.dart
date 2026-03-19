import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (context) => OricliState(),
      child: const OricliApp(),
    ),
  );
}

class OricliState extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  bool _isTyping = false;

  List<ChatMessage> get messages => _messages;
  bool get isTyping => _isTyping;

  Future<void> sendMessage(String text) async {
    _messages.add(ChatMessage(text: text, isUser: true));
    _isTyping = true;
    notifyListeners();

    try {
      // Sovereign API Call to Go Backbone
      final response = await http.post(
        Uri.parse('https://chat.thynaptic.com/v1/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer glm.8eHruhzb.IPtP2toLOSKATWc5f_KXrRQOO6JcvFBB', // Placeholder or dynamic
        },
        body: jsonEncode({
          'model': 'oricli-cognitive',
          'messages': [{'role': 'user', 'content': text}],
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final content = data['choices'][0]['message']['content'];
        _messages.add(ChatMessage(text: content, isUser: false));
      } else {
        _messages.add(ChatMessage(text: "Error: ${response.statusCode}", isUser: false));
      }
    } catch (e) {
      _messages.add(ChatMessage(text: "Connection failed: $e", isUser: false));
    }

    _isTyping = false;
    notifyListeners();
  }
}

class ChatMessage {
  final String text;
  final bool isUser;
  ChatMessage({required this.text, required this.isUser});
}

class OricliApp extends StatelessWidget {
  const OricliApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Oricli Sovereign Portal',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0A0A0A),
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
          primary: Colors.deepPurpleAccent,
        ),
        textTheme: GoogleFonts.robotoMonoTextTheme(ThemeData.dark().textTheme),
      ),
      home: const MainPortal(),
    );
  }
}

class MainPortal extends StatefulWidget {
  const MainPortal({super.key});

  @override
  State<MainPortal> createState() => _MainPortalState();
}

class _MainPortalState extends State<MainPortal> {
  final TextEditingController _controller = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<OricliState>();

    return Scaffold(
      appBar: AppBar(
        title: Text('ORICLI-ALPHA // SOVEREIGN PORTAL', 
          style: GoogleFonts.oswald(letterSpacing: 2, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.black,
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.hub), onPressed: () {}),
          IconButton(icon: const Icon(Icons.settings), onPressed: () {}),
        ],
      ),
      body: Column(
        children: [
          // The Swarm Visualization Area (Placeholder for Phase 3)
          Expanded(
            flex: 2,
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.black,
                border: Border(bottom: BorderSide(color: Colors.white10)),
              ),
              child: Center(
                child: Text('HIVE SWARM VISUALIZATION [PHASE 3]', 
                  style: TextStyle(color: Colors.white24, letterSpacing: 4)),
              ),
            ),
          ),
          
          // Chat Area
          Expanded(
            flex: 3,
            child: ListView.builder(
              padding: const EdgeInsets.all(20),
              itemCount: state.messages.length,
              itemBuilder: (context, index) {
                final msg = state.messages[index];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(msg.isUser ? "USER> " : "ORICLI> ", 
                        style: TextStyle(
                          color: msg.isUser ? Colors.blueAccent : Colors.greenAccent,
                          fontWeight: FontWeight.bold
                        )
                      ),
                      Expanded(child: Text(msg.text)),
                    ],
                  ),
                );
              },
            ),
          ),
          
          if (state.isTyping)
            const LinearProgressIndicator(minHeight: 1, color: Colors.greenAccent),

          // Input Area
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.black,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: "Enter directive...",
                      border: InputBorder.none,
                    ),
                    onSubmitted: (val) {
                      if (val.isNotEmpty) {
                        state.sendMessage(val);
                        _controller.clear();
                      }
                    },
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send, color: Colors.greenAccent),
                  onPressed: () {
                    if (_controller.text.isNotEmpty) {
                      state.sendMessage(_controller.text);
                      _controller.clear();
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
