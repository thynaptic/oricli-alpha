import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:math' as math;
import 'dart:async';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/atom-one-dark.dart';

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

class Artifact {
  final String type;
  final String title;
  final String language;
  final List<String> versions;
  int currentVersion;

  Artifact({
    required this.type,
    required this.title,
    required this.language,
    required String initialContent,
  }) : versions = [initialContent], currentVersion = 0;

  String get content => versions[currentVersion];
}

class ChatSession {
  final String id;
  String title;
  final List<ChatMessage> messages;
  final List<Artifact> artifacts;
  ChatSession({required this.id, required this.title, required this.messages, required this.artifacts});
}

class HiveNode {
  final String name;
  Offset position;
  double pulse = 0.0;
  bool isActive = false;
  HiveNode({required this.name, required this.position});
}

class OricliState extends ChangeNotifier {
  final List<ChatSession> _sessions = [
    ChatSession(id: '1', title: 'Initial Directive', messages: [], artifacts: [])
  ];
  int _currentSessionIndex = 0;
  bool _isTyping = false;
  bool _sidebarVisible = true;
  bool _canvasVisible = true;
  double _mood = 0.5;
  List<HiveNode> _nodes = [];
  Timer? _animationTimer;

  List<ChatSession> get sessions => _sessions;
  ChatSession get currentSession => _sessions[_currentSessionIndex];
  int get currentSessionIndex => _currentSessionIndex;
  bool get isTyping => _isTyping;
  bool get sidebarVisible => _sidebarVisible;
  bool get canvasVisible => _canvasVisible;
  double get mood => _mood;
  List<HiveNode> get nodes => _nodes;

  OricliState() {
    _initializeHive();
    _startAnimations();
  }

  void _initializeHive() {
    final random = math.Random();
    for (var i = 0; i < 269; i++) {
      _nodes.add(HiveNode(
        name: "module_$i",
        position: Offset(random.nextDouble(), random.nextDouble()),
      ));
    }
  }

  void _startAnimations() {
    _animationTimer = Timer.periodic(const Duration(milliseconds: 50), (timer) {
      for (var node in _nodes) {
        if (node.isActive) {
          node.pulse += 0.1;
          if (node.pulse >= 1.0) {
            node.pulse = 0.0;
            node.isActive = false;
          }
        }
      }
      notifyListeners();
    });
  }

  void _triggerSwarm() {
    final random = math.Random();
    for (var i = 0; i < 25; i++) {
      _nodes[random.nextInt(_nodes.length)].isActive = true;
    }
  }

  void toggleSidebar() {
    _sidebarVisible = !_sidebarVisible;
    notifyListeners();
  }

  void toggleCanvas() {
    _canvasVisible = !_canvasVisible;
    notifyListeners();
  }

  void createNewChat() {
    final newSession = ChatSession(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: 'New Directive',
      messages: [],
      artifacts: [],
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

  void _parseArtifacts(String text) {
    // 1. Precise Tag Parsing (High Resilience)
    // Matches <artifact ...>content</artifact>
    final artifactBlockRegex = RegExp(r'<artifact([\s\S]*?)>([\s\S]*?)<\/artifact>', caseSensitive: false);
    final blocks = artifactBlockRegex.allMatches(text);
    
    for (final block in blocks) {
      final attrString = block.group(1) ?? '';
      final content = block.group(2)?.trim() ?? '';
      
      // Extract individual attributes from the attrString
      final type = RegExp(r'type="([^"]*)"').firstMatch(attrString)?.group(1) ?? 'code';
      final title = RegExp(r'title="([^"]*)"').firstMatch(attrString)?.group(1) ?? 'untitled';
      final lang = RegExp(r'language="([^"]*)"').firstMatch(attrString)?.group(1) ?? 'plain';
      
      _addOrUpdateArtifact(type, title, lang, content);
    }

    // 2. Markdown Auto-Promotion (Fallback)
    if (blocks.isEmpty) {
      final mdRegex = RegExp(r'```(\w+)?\n([\s\S]*?)```');
      final mdMatches = mdRegex.allMatches(text);
      for (final match in mdMatches) {
        final lang = match.group(1) ?? 'plain';
        final content = match.group(2)?.trim() ?? '';
        final title = "generated_snippet.${lang == 'python' ? 'py' : lang}";
        _addOrUpdateArtifact('code', title, lang, content);
      }
    }
  }

  void _addOrUpdateArtifact(String type, String title, String language, String content) {
    final existingIndex = currentSession.artifacts.indexWhere((a) => a.title == title);
    if (existingIndex != -1) {
      if (currentSession.artifacts[existingIndex].content != content) {
        currentSession.artifacts[existingIndex].versions.add(content);
        currentSession.artifacts[existingIndex].currentVersion = currentSession.artifacts[existingIndex].versions.length - 1;
      }
    } else {
      currentSession.artifacts.add(Artifact(
        type: type,
        title: title,
        language: language,
        initialContent: content,
      ));
    }
    _canvasVisible = true;
  }

  void setArtifactVersion(int artIndex, int versionIndex) {
    currentSession.artifacts[artIndex].currentVersion = versionIndex;
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    currentSession.messages.add(ChatMessage(text: text, isUser: true));
    
    if (currentSession.messages.length == 1) {
      currentSession.title = text.length > 20 ? "${text.substring(0, 20)}..." : text;
    }
    
    _isTyping = true;
    _triggerSwarm();
    if (text.length > 100) _mood = math.min(1.0, _mood + 0.1);
    
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
        
        // Parse artifacts first so state is ready
        _parseArtifacts(content);
        
        currentSession.messages.add(ChatMessage(text: content, isUser: false));
        _triggerSwarm();
      } else {
        currentSession.messages.add(ChatMessage(text: "Error: ${response.statusCode}", isUser: false));
      }
    } catch (e) {
      currentSession.messages.add(ChatMessage(text: "Connection failed: $e", isUser: false));
    }

    _isTyping = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _animationTimer?.cancel();
    super.dispose();
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
        scaffoldBackgroundColor: Colors.transparent,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
          primary: Colors.deepPurpleAccent,
        ),
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
      child: CustomPaint(painter: _GrainPainter()),
    );
  }
}

class _GrainPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white;
    final random = math.Random();
    for (var i = 0; i < 5000; i++) {
      canvas.drawCircle(Offset(random.nextDouble() * size.width, random.nextDouble() * size.height), 0.5, paint);
    }
  }
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class HiveSwarmPainter extends CustomPainter {
  final List<HiveNode> nodes;
  final double mood;
  HiveSwarmPainter({required this.nodes, required this.mood});

  @override
  void paint(Canvas canvas, Size size) {
    final activePaint = Paint()..color = Color.lerp(Colors.greenAccent, Colors.orangeAccent, mood)!..style = PaintingStyle.fill;
    final inactivePaint = Paint()..color = Colors.white.withOpacity(0.05)..style = PaintingStyle.fill;
    final linePaint = Paint()..color = Colors.white.withOpacity(0.02)..strokeWidth = 0.5;

    for (var i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final pos = Offset(node.position.dx * size.width, node.position.dy * size.height);
      if (i % 12 == 0 && i + 1 < nodes.length) {
        final nextPos = Offset(nodes[i+1].position.dx * size.width, nodes[i+1].position.dy * size.height);
        canvas.drawLine(pos, nextPos, linePaint);
      }
      if (node.isActive) {
        final pulseSize = 2.0 + (node.pulse * 15.0);
        final pulsePaint = Paint()..color = activePaint.color.withOpacity(1.0 - node.pulse)..style = PaintingStyle.fill;
        canvas.drawCircle(pos, pulseSize, pulsePaint);
        canvas.drawCircle(pos, 2, activePaint);
      } else {
        canvas.drawCircle(pos, 1, inactivePaint);
      }
    }
  }
  @override
  bool shouldRepaint(covariant HiveSwarmPainter oldDelegate) => true;
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
      backgroundColor: Colors.transparent,
      drawer: isLargeScreen ? null : const ChatSidebar(),
      appBar: AppBar(
        backgroundColor: Colors.black.withOpacity(0.5),
        flexibleSpace: Container(decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: Colors.white10)))),
        leading: IconButton(
          icon: const Icon(Icons.menu),
          onPressed: () => isLargeScreen ? state.toggleSidebar() : Scaffold.of(context).openDrawer(),
        ),
        title: Text('ORICLI-ALPHA // SOVEREIGN PORTAL', style: GoogleFonts.oswald(letterSpacing: 2, fontWeight: FontWeight.bold, fontSize: 18)),
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(state.canvasVisible ? Icons.view_sidebar_rounded : Icons.view_sidebar_outlined, color: state.canvasVisible ? Colors.greenAccent : Colors.white54),
            onPressed: () => state.toggleCanvas(),
          ),
          IconButton(icon: const Icon(Icons.hub_outlined), onPressed: () {}),
        ],
      ),
      body: Row(
        children: [
          if (isLargeScreen && state.sidebarVisible)
            const SizedBox(width: 280, child: ChatSidebar()),
          
          Expanded(
            flex: 3,
            child: Column(
              children: [
                Expanded(
                  flex: 2,
                  child: Container(
                    width: double.infinity,
                    decoration: BoxDecoration(color: Colors.black.withOpacity(0.3), border: const Border(bottom: BorderSide(color: Colors.white10))),
                    child: Stack(
                      children: [
                        Positioned.fill(child: CustomPaint(painter: HiveSwarmPainter(nodes: state.nodes, mood: state.mood))),
                        Positioned(
                          top: 20, left: 20,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                            decoration: BoxDecoration(color: Colors.black.withOpacity(0.5), border: Border.all(color: Colors.greenAccent.withOpacity(0.3)), borderRadius: BorderRadius.circular(4)),
                            child: Row(mainAxisSize: MainAxisSize.min, children: [
                              const Icon(Icons.lens, color: Colors.greenAccent, size: 8),
                              const SizedBox(width: 8),
                              Text('HIVE SWARM: ACTIVE', style: GoogleFonts.robotoMono(color: Colors.greenAccent, fontSize: 10, letterSpacing: 1)),
                            ]),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                
                Expanded(
                  flex: 5,
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                    itemCount: state.currentSession.messages.length,
                    itemBuilder: (context, index) => ChatBubble(msg: state.currentSession.messages[index]),
                  ),
                ),
                
                if (state.isTyping) const LinearProgressIndicator(minHeight: 1, color: Colors.greenAccent),

                Container(
                  padding: const EdgeInsets.all(24),
                  child: Center(
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 800),
                      decoration: BoxDecoration(color: Colors.black.withOpacity(0.6), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white10)),
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                      child: Row(children: [
                        Expanded(
                          child: TextField(
                            controller: _controller,
                            style: const TextStyle(fontSize: 14),
                            decoration: const InputDecoration(hintText: "Enter directive...", hintStyle: TextStyle(color: Colors.white24), border: InputBorder.none),
                            onSubmitted: (val) { if (val.isNotEmpty) { state.sendMessage(val); _controller.clear(); } },
                          ),
                        ),
                        IconButton(icon: const Icon(Icons.arrow_upward_rounded, color: Colors.greenAccent, size: 20), onPressed: () { if (_controller.text.isNotEmpty) { state.sendMessage(_controller.text); _controller.clear(); } }),
                      ]),
                    ),
                  ),
                ),
              ],
            ),
          ),

          if (isLargeScreen && state.canvasVisible)
            const SizedBox(width: 600, child: LiveCanvasPanel()),
        ],
      ),
    );
  }
}

class LiveCanvasPanel extends StatelessWidget {
  const LiveCanvasPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<OricliState>();
    final artifacts = state.currentSession.artifacts;

    return Container(
      color: Colors.black.withOpacity(0.4),
      decoration: const BoxDecoration(border: Border(left: BorderSide(color: Colors.white10))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: Row(
              children: [
                const Icon(Icons.auto_awesome_mosaic_outlined, size: 18, color: Colors.greenAccent),
                const SizedBox(width: 12),
                Text("LIVE CANVAS", style: GoogleFonts.oswald(letterSpacing: 2, fontWeight: FontWeight.bold, fontSize: 16)),
                const Spacer(),
                Text("${artifacts.length} ARTIFACTS", style: GoogleFonts.robotoMono(fontSize: 10, color: Colors.white24)),
              ],
            ),
          ),
          if (artifacts.isEmpty)
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.dashboard_customize_outlined, size: 48, color: Colors.white10),
                    const SizedBox(height: 16),
                    Text("No artifacts detected yet.", style: TextStyle(color: Colors.white10, fontSize: 12)),
                  ],
                ),
              ),
            )
          else
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: artifacts.length,
                itemBuilder: (context, index) {
                  final art = artifacts[index];
                  return ArtifactRenderer(art: art, index: index);
                },
              ),
            ),
        ],
      ),
    );
  }
}

class ArtifactRenderer extends StatelessWidget {
  final Artifact art;
  final int index;
  const ArtifactRenderer({super.key, required this.art, required this.index});

  @override
  Widget build(BuildContext context) {
    final state = context.read<OricliState>();

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            leading: Icon(art.type == 'code' ? Icons.code : Icons.description_outlined, color: Colors.blueAccent, size: 18),
            title: Text(art.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
            subtitle: Text(art.type.toUpperCase(), style: const TextStyle(fontSize: 9, color: Colors.white24)),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (art.versions.length > 1)
                  DropdownButton<int>(
                    value: art.currentVersion,
                    underline: Container(),
                    dropdownColor: const Color(0xFF151515),
                    items: List.generate(art.versions.length, (i) => DropdownMenuItem(
                      value: i,
                      child: Text("V${i+1}", style: const TextStyle(fontSize: 10)),
                    )),
                    onChanged: (v) => state.setArtifactVersion(index, v!),
                  ),
                IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 14, color: Colors.white24),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: art.content));
                    ScaffoldMessenger.of(context).showSnackBar(ApiResponseSnackBar(message: "Copied to clipboard"));
                  },
                ),
              ],
            ),
          ),
          if (art.type == 'code')
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Colors.white10)),
              ),
              child: HighlightView(
                art.content,
                language: art.language,
                theme: atomOneDarkTheme,
                padding: const EdgeInsets.all(8),
                textStyle: GoogleFonts.robotoMono(fontSize: 12),
              ),
            )
          else
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Colors.white10)),
              ),
              child: SelectableText(
                art.content,
                style: const TextStyle(fontSize: 13, height: 1.5, color: Colors.white70),
              ),
            ),
        ],
      ),
    );
  }
}

class ApiResponseSnackBar extends SnackBar {
  final String message;
  ApiResponseSnackBar({super.key, required this.message}) : super(
    content: Text(message, style: const TextStyle(fontSize: 12)),
    backgroundColor: Colors.deepPurple,
    behavior: SnackBarBehavior.floating,
    duration: const Duration(seconds: 2),
  );
}

class ChatBubble extends StatelessWidget {
  final ChatMessage msg;
  const ChatBubble({super.key, required this.msg});

  @override
  Widget build(BuildContext context) {
    final displayContent = msg.text.replaceAll(RegExp(r'<artifact[\s\S]*?<\/artifact>'), "[ARTIFACT GENERATED - SEE CANVAS]");

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: msg.isUser ? Colors.blueAccent.withOpacity(0.1) : Colors.greenAccent.withOpacity(0.1), borderRadius: BorderRadius.circular(4), border: Border.all(color: msg.isUser ? Colors.blueAccent.withOpacity(0.2) : Colors.greenAccent.withOpacity(0.2))),
            child: Icon(msg.isUser ? Icons.person_outline : Icons.auto_awesome_outlined, size: 14, color: msg.isUser ? Colors.blueAccent : Colors.greenAccent),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(msg.isUser ? "COMMANDER" : "ORICLI-ALPHA", style: GoogleFonts.oswald(fontSize: 10, letterSpacing: 1.5, color: Colors.white38, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                SelectableText(displayContent, style: TextStyle(height: 1.6, fontSize: 14, color: Colors.white.withOpacity(0.9))),
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
    showDialog(context: context, builder: (context) => AlertDialog(
      backgroundColor: const Color(0xFF151515),
      title: Text("Rename Directive", style: GoogleFonts.oswald(fontSize: 16)),
      content: TextField(controller: controller, autofocus: true, style: const TextStyle(fontSize: 14), decoration: const InputDecoration(border: OutlineInputBorder(), enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white10)))),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text("CANCEL")),
        TextButton(onPressed: () { state.renameSession(index, controller.text); Navigator.pop(context); }, child: const Text("RENAME", style: TextStyle(color: Colors.greenAccent))),
      ],
    ));
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<OricliState>();
    return Container(
      color: Colors.black.withOpacity(0.4),
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.all(20.0),
          child: ElevatedButton.icon(
            onPressed: () => state.createNewChat(),
            icon: const Icon(Icons.add, size: 16),
            label: Text("NEW DIRECTIVE", style: GoogleFonts.oswald(letterSpacing: 1)),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.white.withOpacity(0.05), foregroundColor: Colors.white, elevation: 0, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)), side: const BorderSide(color: Colors.white10)),
          ),
        ),
        Expanded(child: ListView.builder(itemCount: state.sessions.length, itemBuilder: (context, index) {
          final session = state.sessions[index];
          final isSelected = state.currentSessionIndex == index;
          return Padding(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2), child: ListTile(
            title: Text(session.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: isSelected ? Colors.white : Colors.white38, fontSize: 13, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
            selectedTileColor: Colors.white.withOpacity(0.05),
            onTap: () { state.switchSession(index); if (MediaQuery.of(context).size.width <= 900) Navigator.pop(context); },
            trailing: isSelected ? Row(mainAxisSize: MainAxisSize.min, children: [

              IconButton(icon: const Icon(Icons.edit_outlined, size: 14, color: Colors.white24), onPressed: () => _showRenameDialog(context, state, index)),
              IconButton(icon: const Icon(Icons.delete_outline_rounded, size: 14, color: Colors.white24), onPressed: () => state.deleteSession(index)),
            ]) : null,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), contentPadding: const EdgeInsets.symmetric(horizontal: 16),
          ));
        })),
        Container(width: double.infinity, height: 1, color: Colors.white10),
        Padding(padding: const EdgeInsets.all(20.0), child: Row(children: [
          Container(padding: const EdgeInsets.all(2), decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.deepPurpleAccent.withOpacity(0.5))), child: const CircleAvatar(backgroundColor: Colors.transparent, radius: 12, child: Icon(Icons.shield_outlined, size: 14, color: Colors.deepPurpleAccent))),
          const SizedBox(width: 12),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text("SOVEREIGN USER", style: TextStyle(fontSize: 11, color: Colors.white70, fontWeight: FontWeight.bold)),
            Text("LEVEL: ALPHA", style: TextStyle(fontSize: 9, color: Colors.white24, letterSpacing: 1)),
          ]),
        ])),
      ]),
    );
  }
}
