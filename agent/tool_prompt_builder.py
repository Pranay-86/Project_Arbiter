def build_tool_prompt(tools: list) -> str:
    """
    Builds a detailed tool reference injected into every LLM prompt.
    Shows exact parameter names and a concrete call example per tool.
    """

    _EXAMPLES = {
        # Apps
        "open_application":  '{"action": "open_application",  "parameters": {"app": "notepad"}}',
        "close_application": '{"action": "close_application", "parameters": {"app": "notepad"}}',
        # Files
        "read_file":         '{"action": "read_file",         "parameters": {"path": "C:/Users/me/notes.txt"}}',
        "write_file":        '{"action": "write_file",        "parameters": {"path": "hello.py", "content": "print(\'hello\')"}}',
        "append_file":       '{"action": "append_file",       "parameters": {"path": "log.txt", "content": "new line"}}',
        "copy_file":         '{"action": "copy_file",         "parameters": {"source": "file.txt", "destination": "backup/file.txt"}}',
        "move_file":         '{"action": "move_file",         "parameters": {"source": "old.txt", "destination": "new.txt"}}',
        "delete_file":       '{"action": "delete_file",       "parameters": {"path": "C:/Users/me/temp.txt"}}',
        "list_files":        '{"action": "list_files",        "parameters": {"path": "Documents"}}',
        "search_files":      '{"action": "search_files",      "parameters": {"folder": "C:/Users/me", "name": "*.py", "content": ""}}',
        "create_folder":     '{"action": "create_folder",     "parameters": {"path": "C:/Users/me/NewFolder"}}',
        "open_file":         '{"action": "open_file",         "parameters": {"path": "C:/Users/me/video.mp4"}}',
        "zip_files":         '{"action": "zip_files",         "parameters": {"action": "zip", "source": "myfolder", "destination": "myfolder.zip"}}',
        # Execution
        "run_python":        '{"action": "run_python",        "parameters": {"code": "print(2 + 2)"}}',
        "run_command":       '{"action": "run_command",       "parameters": {"command": "dir C:\\\\Users", "shell": "cmd"}}',
        # Web
        "search_web":        '{"action": "search_web",        "parameters": {"query": "latest Python tutorials"}}',
        "search_arxiv":      '{"action": "search_arxiv",      "parameters": {"query": "transformer attention"}}',
        "read_webpage":      '{"action": "read_webpage",      "parameters": {"url": "https://example.com"}}',
        "download_paper":    '{"action": "download_paper",    "parameters": {"url": "https://arxiv.org/pdf/1706.03762"}}',
        "download_file":     '{"action": "download_file",     "parameters": {"url": "https://example.com/file.zip", "filename": "file.zip"}}',
        "open_url":          '{"action": "open_url",          "parameters": {"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}}',
        "search_youtube":    '{"action": "search_youtube",    "parameters": {"query": "lofi hip hop"}}',
        # System
        "system_info":       '{"action": "system_info",       "parameters": {}}',
        "get_processes":     '{"action": "get_processes",     "parameters": {"filter": "chrome"}}',
        "kill_process":      '{"action": "kill_process",      "parameters": {"name": "notepad"}}',
        "take_screenshot":   '{"action": "take_screenshot",   "parameters": {"path": ""}}',
        "get_active_window": '{"action": "get_active_window", "parameters": {}}',
        "get_clipboard":     '{"action": "get_clipboard",     "parameters": {}}',
        "set_clipboard":     '{"action": "set_clipboard",     "parameters": {"content": "text to copy"}}',
        "type_text":         '{"action": "type_text",         "parameters": {"text": "Hello world", "hotkey": "", "delay": "1"}}',
        "mouse_click":       '{"action": "mouse_click",       "parameters": {"x": "960", "y": "540", "button": "left"}}',
        "play_media":        '{"action": "play_media",        "parameters": {"path": "C:/Videos/movie.mp4"}}',
        "notify":            '{"action": "notify",            "parameters": {"title": "Done", "message": "Task completed"}}',
        "get_env_vars":      '{"action": "get_env_vars",      "parameters": {"name": "PATH"}}',
        # Final
        "final_answer":      '{"action": "final_answer",      "parameters": {"answer": "The result is..."}}',
    }

    if not tools:
        return "No tools available.\n"

    lines = [
        "AVAILABLE TOOLS",
        "Use EXACT parameter names shown. Wrong names cause failures.\n",
    ]

    for tool in tools:
        name   = tool.get("name", "?")
        desc   = tool.get("description", "").strip()
        params = tool.get("parameters", {})

        lines.append(f"── {name}")
        if desc:
            short = desc[:120] + "..." if len(desc) > 120 else desc
            lines.append(f"   {short}")

        if params:
            param_str = ", ".join(
                f"{k}: {v.split()[0]}" for k, v in params.items()
            )
            lines.append(f"   Params: {param_str}")
        else:
            lines.append("   Params: none")

        example = _EXAMPLES.get(name)
        if example:
            lines.append(f"   Example: {example}")

        lines.append("")

    return "\n".join(lines)
