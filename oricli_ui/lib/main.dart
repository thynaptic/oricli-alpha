import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:math' as math;

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
  double _mood = 0.5; // 0.0 (calm/blue) to 1.0 (volatile/red)

  List<ChatSession> get sessions => _sessions;
  ChatSession get currentSession => _sessions[_currentSessionIndex];
  int get currentSessionIndex => _currentSessionIndex;
  bool get isTyping => _isTyping;
  bool get sidebarVisible => _sidebarVisible;
  double get mood => _mood;

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
    // Simulate mood shift based on input complexity (pseudo-metacognition)
    if (text.length > 100) _mood = math.min(1.0, _mood + 0.1);
    if (text.contains("?")) _mood = math.max(0.0, _mood - 0.05);
    
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

// Phase 2: Thynaptic Theme Extensions
@immutable
class ThynapticTheme extends ThemeExtension<ThynapticTheme> {
  final Color? glowColor;
  final double glowOpacity;

  const ThynapticTheme({this.glowColor, this.glowOpacity = 0.5});

  @override
  ThynapticTheme copyWith({Color? glowColor, double? glowOpacity}) {
    return ThynapticTheme(
      glowColor: glowColor ?? this.glowColor,
      glowOpacity: glowOpacity ?? this.glowOpacity,
    );
  }

  @override
  ThynapticTheme lerp(ThemeExtension<ThynapticTheme>? other, double t) {
    if (other is! ThynapticTheme) return this;
    return ThynapticTheme(
      glowColor: Color.lerp(glowColor, other.glowColor, t),
      glowOpacity: lerpDouble(glowOpacity, other.glowOpacity, t) ?? 0.5,
    );
  }

  double? lerpDouble(double? a, double? b, double t) {
    if (a == null && b == null) return null;
    a ??= 0.0;
    b ??= 0.0;
    return a + (b - a) * t;
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
        scaffoldBackgroundColor: Colors.transparent, // Allow gradient to show through
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
          primary: Colors.deepPurpleAccent,
        ),
        extensions: const [
          ThynapticTheme(glowColor: Colors.deepPurpleAccent, glowOpacity: 0.3),
        ],
        textTheme: GoogleFonts.robotoMonoTextTheme(ThemeData.dark().textTheme),
      ),
      home: const SubconsciousBackground(child: MainPortal()),
    );
  }
}

class SubconsciousBackground extends StatelessWidget {
  final Widget child;
  const SubconsciousBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final mood = context.select<OricliState, double>((s) => s.mood);
    
    // Smooth color transition based on mood
    final primaryColor = Color.lerp(Colors.deepPurple.shade900, Colors.red.shade900, mood)!;
    final secondaryColor = Color.lerp(Colors.blue.shade900, Colors.orange.shade900, mood)!;

    return AnimatedContainer(
      duration: const Duration(seconds: 2),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            primaryColor.withOpacity(0.8),
            Colors.black,
            secondaryColor.withOpacity(0.6),
          ],
          stops: const [0.0, 0.5, 1.0],
        ),
      ),
      child: Stack(
        children: [
          // Noise/Grain Overlay
          const Positioned.fill(child: GrainOverlay()),
          child,
        ],
      ),
    );
  }
}

class GrainOverlay extends StatelessWidget {
  const GrainOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: 0.03,
      child: CustomPaint(
        painter: _GrainPainter(),
      ),
    );
  }
}

class _GrainPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white;
    final random = math.Random();
    for (var i = 0; i < 5000; i++) {
      canvas.drawCircle(
        Offset(random.nextDouble() * size.width, random.nextDouble() * size.height),
        0.5,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
      backgroundColor: Colors.transparent, // Background handled by parent
      drawer: isLargeScreen ? null : const ChatSidebar(),
      appBar: AppBar(
        backgroundColor: Colors.black.withOpacity(0.5),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: Colors.white10)),
          ),
        ),
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
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.hub_outlined), onPressed: () {}),
        ],
      ),
      body: Row(
        children: [
          if (isLargeScreen && state.sidebarVisible)
            const SizedBox(
              width: 280,
              child: ChatSidebar(),
            ),
          Expanded(
            child: Column(
              children: [
                // Swarm Canvas Placeholder (Glowing)
                Expanded(
                  flex: 1,
                  child: Container(
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.3),
                      border: const Border(bottom: BorderSide(color: Colors.white10)),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                            decoration: BoxDecoration(
                              border: Border.all(color: Colors.greenAccent.withOpacity(0.3)),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text('HIVE STATUS: NOMINAL', 
                              style: TextStyle(color: Colors.greenAccent, fontSize: 10, letterSpacing: 2)),
                          ),
                          const SizedBox(height: 12),
                          const Text('HIVE SWARM VISUALIZATION [PHASE 3]', 
                            style: TextStyle(color: Colors.white24, letterSpacing: 4, fontSize: 10)),
                        ],
                      ),
                    ),
                  ),
                ),
                
                // Chat Area
                Expanded(
                  flex: 4,
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                    itemCount: state.currentSession.messages.length,
                    itemBuilder: (context, index) {
                      final msg = state.currentSession.messages[index];
                      return ChatBubble(msg: msg);
                    },
                  ),
                ),
                
                if (state.isTyping)
                  const LinearProgressIndicator(minHeight: 1, color: Colors.greenAccent),

                // Input Area
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 32),
                  child: Center(
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 850),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.6),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.white10),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.5),
                            blurRadius: 20,
                            offset: const Offset(0, 10),
                          ),
                        ],
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _controller,
                              style: const TextStyle(fontSize: 14),
                              decoration: const InputDecoration(
                                hintText: "Enter directive...",
                                hintStyle: TextStyle(color: Colors.white24),
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
                            icon: const Icon(Icons.arrow_upward_rounded, color: Colors.greenAccent, size: 20),
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

class ChatBubble extends StatelessWidget {
  final ChatMessage msg;
  const ChatBubble({super.key, required this.msg});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 2),
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: msg.isUser ? Colors.blueAccent.withOpacity(0.1) : Colors.greenAccent.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: msg.isUser ? Colors.blueAccent.withOpacity(0.2) : Colors.greenAccent.withOpacity(0.2)),
            ),
            child: Icon(
              msg.isUser ? Icons.person_outline : Icons.auto_awesome_outlined,
              size: 14,
              color: msg.isUser ? Colors.blueAccent : Colors.greenAccent,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  msg.isUser ? "COMMANDER" : "ORICLI-ALPHA",
                  style: GoogleFonts.oswald(
                    fontSize: 10,
                    letterSpacing: 1.5,
                    color: Colors.white38,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                SelectableText(
                  msg.text,
                  style: TextStyle(
                    height: 1.6,
                    fontSize: 14,
                    color: Colors.white.withOpacity(0.9),
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
        title: Text("Rename Directive", style: GoogleFonts.oswald(fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: const TextStyle(fontSize: 14),
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white10)),
          ),
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
      color: Colors.black.withOpacity(0.4),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: ElevatedButton.icon(
              onPressed: () => state.createNewChat(),
              icon: const Icon(Icons.add, size: 16),
              label: Text("NEW DIRECTIVE", style: GoogleFonts.oswald(letterSpacing: 1)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white.withOpacity(0.05),
                foregroundColor: Colors.white,
                elevation: 0,
                minimumSize: const Size(double.infinity, 50),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
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
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                  child: ListTile(
                    title: Text(
                      session.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isSelected ? Colors.white : Colors.white38,
                        fontSize: 13,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
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
                          icon: const Icon(Icons.edit_outlined, size: 14, color: Colors.white24),
                          onPressed: () => _showRenameDialog(context, state, index),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline_rounded, size: 14, color: Colors.white24),
                          onPressed: () => state.deleteSession(index),
                        ),
                      ],
                    ) : null,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                  ),
                );
              },
            ),
          ),
          Container(width: double.infinity, height: 1, color: Colors.white10),
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.deepPurpleAccent.withOpacity(0.5)),
                  ),
                  child: const CircleAvatar(
                    backgroundColor: Colors.transparent,
                    radius: 12,
                    child: Icon(Icons.shield_outlined, size: 14, color: Colors.deepPurpleAccent),
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("SOVEREIGN USER", style: TextStyle(fontSize: 11, color: Colors.white70, fontWeight: FontWeight.bold)),
                    Text("LEVEL: ALPHA", style: TextStyle(fontSize: 9, color: Colors.white24, letterSpacing: 1)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
