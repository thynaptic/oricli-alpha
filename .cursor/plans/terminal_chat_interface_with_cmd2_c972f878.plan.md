---
name: Terminal Chat Interface with cmd2
overview: Build a fully functional terminal chat interface using cmd2 that integrates with Mavaia's brain system, providing persistent chats, command history, code analysis capabilities, and a polished UI experience similar to ChatGPT/Claude CLI.
todos:
  - id: setup-cli-structure
    content: Create oricli_core/cli/ directory structure with __init__.py and base module files
    status: pending
  - id: implement-session-manager
    content: Implement SessionManager class with persistence using Mavaia state storage (save, load, list, delete sessions)
    status: pending
  - id: implement-formatter
    content: Create Formatter class with message formatting, code block detection, and ANSI color support
    status: pending
  - id: implement-main-cli
    content: Create ChatCLI class extending cmd2.Cmd with MavaiaClient integration, chat message handling, and custom commands (/new, /load, /save, /sessions, /delete, /modules, /code, /clear, /help)
    status: pending
  - id: add-code-analysis
    content: Integrate code_analysis module and python namespace methods for code-to-code capabilities with formatted output
    status: pending
  - id: polish-ui
    content: Add welcome message, loading indicators, error formatting, and enhance overall UI polish
    status: pending
  - id: update-dependencies
    content: Add cmd2 and rich to pyproject.toml dependencies and create entry point script
    status: pending
  - id: testing
    content: Test all commands, session persistence, error handling, and create usage documentation
    status: pending
---

# Terminal Chat Interface with cmd2

## Overview

Create a production-ready terminal chat interface using `cmd2` that provides full access to Mavaia's cognitive capabilities, including code analysis, persistent conversations, command history, and an intuitive CLI experience.

## Architecture

### Core Components

1. **Main CLI Application** (`oricli_core/cli/chat_cli.py`)

   - Extends `cmd2.Cmd` for interactive terminal interface
   - Integrates with `MavaiaClient` for brain operations
   - Manages chat sessions and conversation state
   - Provides command history via cmd2's built-in features

2. **Chat Session Manager** (`oricli_core/cli/session_manager.py`)

   - Manages persistent chat sessions
   - Uses Mavaia's state storage system for persistence
   - Handles session creation, loading, saving, and listing
   - Tracks conversation history per session

3. **UI Formatter** (`oricli_core/cli/formatter.py`)

   - Formats messages with colors and styling
   - Handles code block formatting
   - Provides progress indicators for long operations
   - Uses ANSI colors for better readability

4. **Command Handlers** (within `chat_cli.py`)

   - Chat commands (send messages, continue conversations)
   - Session management commands (new, load, save, list, delete)
   - Module commands (list modules, execute operations)
   - Code analysis commands (analyze, explain, review code)
   - Utility commands (help, clear, exit)

## Implementation Details

### File Structure

```
oricli_core/cli/
├── __init__.py
├── chat_cli.py          # Main CLI application
├── session_manager.py   # Session persistence
└── formatter.py         # UI formatting utilities
```

### Key Features

1. **Interactive Chat Mode**

   - Default mode: typing messages sends them to Mavaia
   - Multi-line input support (cmd2's multiline commands)
   - Streaming responses (if supported by cognitive generator)
   - Code block detection and formatting

2. **Persistent Sessions**

   - Save conversations to disk using state storage
   - Load previous conversations
   - List all saved sessions
   - Delete sessions
   - Auto-save after each message

3. **Command System**

   - Built-in cmd2 commands (history, alias, etc.)
   - Custom commands:
     - `/new` - Start new chat session
     - `/load <session_id>` - Load a session
     - `/save [session_id]` - Save current session
     - `/sessions` - List all sessions
     - `/delete <session_id>` - Delete a session
     - `/modules` - List available brain modules
     - `/code <operation> <code>` - Execute code analysis
     - `/clear` - Clear screen
     - `/help` - Show help

4. **Code Analysis Integration**

   - Direct access to `code_analysis` module
   - Access to `python` namespace methods
   - Code-to-code reasoning capabilities
   - Syntax highlighting for code blocks

5. **UI Enhancements**

   - Color-coded messages (user vs assistant)
   - Progress indicators
   - Timestamps (optional)
   - Clean formatting for code blocks
   - Error message formatting

### Integration Points

1. **MavaiaClient Integration**
   ```python
   client = MavaiaClient()
   response = client.chat.completions.create(
       model="mavaia-cognitive",
       messages=[{"role": "user", "content": user_message}]
   )
   ```

2. **State Storage Integration**
   ```python
   from oricli_core.brain.state_storage import get_storage
   storage = get_storage()
   storage.save("conversation", session_id, conversation_data)
   ```

3. **Code Analysis Integration**
   ```python
   result = client.brain.code_analysis.analyze_code(code=code)
   result = client.python.analyze_code(code)
   ```


### Dependencies

- Add `cmd2>=2.4.0` to `pyproject.toml` dependencies
- Add `rich>=13.0.0` for enhanced terminal formatting (optional but recommended)

### Entry Point

Add to `pyproject.toml`:

```toml
[project.scripts]
mavaia-chat = "oricli_core.cli.chat_cli:main"
```

## Implementation Steps

1. **Setup CLI Structure**

   - Create `oricli_core/cli/` directory
   - Add `__init__.py`
   - Create base CLI class structure

2. **Implement Session Manager**

   - Create session persistence using state storage
   - Implement session CRUD operations
   - Add session metadata tracking

3. **Implement Formatter**

   - Add message formatting utilities
   - Implement code block detection and formatting
   - Add color schemes

4. **Implement Main CLI**

   - Extend cmd2.Cmd
   - Integrate MavaiaClient
   - Implement chat message handling
   - Add custom commands
   - Integrate session manager

5. **Add Code Analysis Commands**

   - Integrate code_analysis module
   - Add code-to-code capabilities
   - Format code analysis results

6. **Polish UI**

   - Add welcome message
   - Improve error handling
   - Add loading indicators
   - Enhance formatting

7. **Testing & Documentation**

   - Test all commands
   - Test session persistence
   - Add docstrings
   - Create usage examples

## Files to Create/Modify

### New Files

- `oricli_core/cli/__init__.py`
- `oricli_core/cli/chat_cli.py` (~500-800 lines)
- `oricli_core/cli/session_manager.py` (~200-300 lines)
- `oricli_core/cli/formatter.py` (~150-200 lines)

### Modified Files

- `pyproject.toml` - Add cmd2 dependency and entry point
- `oricli_core/__init__.py` - Export CLI if needed

## Considerations

1. **Error Handling**

   - Graceful handling of module failures
   - Clear error messages for users
   - Fallback behavior when modules unavailable

2. **Performance**

   - Async operations where possible
   - Progress indicators for long operations
   - Caching of module metadata

3. **User Experience**

   - Intuitive command syntax
   - Helpful error messages
   - Auto-completion for commands
   - Command history navigation

4. **State Management**

   - Thread-safe session operations
   - Atomic save operations
   - Session versioning for compatibility