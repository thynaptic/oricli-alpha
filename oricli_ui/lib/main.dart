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

class ChatMessage {
  final String text;
  final bool isUser;
  ChatMessage({required this.text, required this.isUser});
}

class ChatSession {
  final String id;
  String title;
  final List<ChatMessage> messages;
  ChatSession({required this.id, required this.title, required this.messages});
}

class OricliState extends ChangeNotifier {
  final List<ChatSession> _sessions = [
    ChatSession(id: '1', title: 'Initial Directive', messages: [])
  ];
  int _currentSessionIndex = 0;
  bool _isTyping = false;
  bool _sidebarVisible = true;

  List<ChatSession> get sessions => _sessions;
  ChatSession get currentSession => _sessions[_currentSessionIndex];
  int get currentSessionIndex => _currentSessionIndex;
  bool get isTyping => _isTyping;
  bool get sidebarVisible => _sidebarVisible;

  void toggleSidebar() {
    _sidebarVisible = !_sidebarVisible;
    notifyListeners();
  }

  void createNewChat() {
    final newSession = ChatSession(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: 'New Directive',
      messages: [],
    );
    _sessions.insert(0, newSession);
    _currentSessionIndex = 0;
    notifyListeners();
  }

  void switchSession(int index) {
    _currentSessionIndex = index;
    notifyListeners();
  }

  void renameSession(int index, String newTitle) {
    _sessions[index].title = newTitle;
    notifyListeners();
  }

  void deleteSession(int index) {
    if (_sessions.length <= 1) return;
    _sessions.removeAt(index);
    if (_currentSessionIndex >= _sessions.length) {
      _currentSessionIndex = _sessions.length - 1;
    }
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    currentSession.messages.add(ChatMessage(text: text, isUser: true));
    
    if (currentSession.messages.length == 1) {
      currentSession.title = text.length > 20 ? "${text.substring(0, 20)}..." : text;
    }
    
    _isTyping = true;
    notifyListeners();

    try {
      final response = await http.post(
        Uri.parse('https://chat.thynaptic.com/v1/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer glm.8eHruhzb.IPtP2toLOSKATWc5f_KXrRQOO6JcvFBB',
        },
        body: jsonEncode({
          'model': 'oricli-cognitive',
          'messages': [{'role': 'user', 'content': text}],
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final content = data['choices'][0]['message']['content'];
        currentSession.messages.add(ChatMessage(text: content, isUser: false));
      } else {
        currentSession.messages.add(ChatMessage(text: "Error: ${response.statusCode}", isUser: false));
      }
    } catch (e) {
      currentSession.messages.add(ChatMessage(text: "Connection failed: $e", isUser: false));
    }

    _isTyping = false;
    notifyListeners();
  }
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
    final isLargeScreen = MediaQuery.of(context).size.width > 900;

    return Scaffold(
      drawer: isLargeScreen ? null : const ChatSidebar(),
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.menu),
          onPressed: () {
            if (isLargeScreen) {
              state.toggleSidebar();
            } else {
              Scaffold.of(context).openDrawer();
            }
          },
        ),
        title: Text('ORICLI-ALPHA // SOVEREIGN PORTAL', 
          style: GoogleFonts.oswald(letterSpacing: 2, fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: Colors.black,
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.hub), onPressed: () {}),
        ],
      ),
      body: Row(
        children: [
          if (isLargeScreen && state.sidebarVisible)
            const SizedBox(
              width: 300,
              child: ChatSidebar(),
            ),
          if (isLargeScreen && state.sidebarVisible)
            Container(width: 1, color: Colors.white10),
          Expanded(
            child: Column(
              children: [
                Expanded(
                  flex: 1,
                  child: Container(
                    width: double.infinity,
                    decoration: const BoxDecoration(
                      color: Colors.black,
                      border: Border(bottom: BorderSide(color: Colors.white10)),
                    ),
                    child: const Center(
                      child: Text('HIVE SWARM VISUALIZATION [PHASE 3]', 
                        style: TextStyle(color: Colors.white24, letterSpacing: 4, fontSize: 10)),
                    ),
                  ),
                ),
                Expanded(
                  flex: 4,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(20),
                    itemCount: state.currentSession.messages.length,
                    itemBuilder: (context, index) {
                      final msg = state.currentSession.messages[index];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(msg.isUser ? "USER> " : "ORICLI> ", 
                              style: TextStyle(
                                color: msg.isUser ? Colors.blueAccent : Colors.greenAccent,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              )
                            ),
                            Expanded(child: SelectableText(msg.text, style: const TextStyle(height: 1.5))),
                          ],
                        ),
                      );
                    },
                  ),
                ),
                if (state.isTyping)
                  const LinearProgressIndicator(minHeight: 1, color: Colors.greenAccent),
                Container(
                  padding: const EdgeInsets.all(24),
                  color: Colors.black,
                  child: Center(
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 800),
                      decoration: BoxDecoration(
                        color: const Color(0xFF151515),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white10),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 16),
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
                            icon: const Icon(Icons.arrow_upward, color: Colors.greenAccent),
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
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class ChatSidebar extends StatelessWidget {
  const ChatSidebar({super.key});

  void _showRenameDialog(BuildContext context, OricliState state, int index) {
    final controller = TextEditingController(text: state.sessions[index].title);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF151515),
        title: const Text("Rename Directive", style: TextStyle(fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(border: OutlineInputBorder()),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("CANCEL")),
          TextButton(
            onPressed: () {
              state.renameSession(index, controller.text);
              Navigator.pop(context);
            },
            child: const Text("RENAME", style: TextStyle(color: Colors.greenAccent)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<OricliState>();

    return Container(
      color: const Color(0xFF050505),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton.icon(
              onPressed: () => state.createNewChat(),
              icon: const Icon(Icons.add, size: 18),
              label: const Text("NEW DIRECTIVE"),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF151515),
                foregroundColor: Colors.white,
                minimumSize: const Size(double.infinity, 48),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                side: const BorderSide(color: Colors.white10),
              ),
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: state.sessions.length,
              itemBuilder: (context, index) {
                final session = state.sessions[index];
                final isSelected = state.currentSessionIndex == index;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  child: ListTile(
                    title: Text(
                      session.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isSelected ? Colors.white : Colors.white54,
                        fontSize: 13,
                      ),
                    ),
                    selected: isSelected,
                    selectedTileColor: Colors.white.withOpacity(0.05),
                    onTap: () {
                      state.switchSession(index);
                      if (MediaQuery.of(context).size.width <= 900) {
                        Navigator.pop(context);
                      }
                    },
                    trailing: isSelected ? Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.edit, size: 14, color: Colors.white38),
                          onPressed: () => _showRenameDialog(context, state, index),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete, size: 14, color: Colors.white38),
                          onPressed: () => state.deleteSession(index),
                        ),
                      ],
                    ) : null,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                  ),
                );
              },
            ),
          ),
          Container(width: double.infinity, height: 1, color: Colors.white10),
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Row(
              children: [
                CircleAvatar(backgroundColor: Colors.deepPurple, radius: 12, child: Icon(Icons.person, size: 14, color: Colors.white)),
                SizedBox(width: 12),
                Text("SOVEREIGN USER", style: TextStyle(fontSize: 12, color: Colors.white70)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
