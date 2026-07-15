#!/usr/bin/env python3
"""PreToolUse-хук: не пропускать Edit/Write/Bash, ломающие или запускающие битый код.

Edit/Write: строит содержимое файла, каким оно станет ПОСЛЕ правки, и проверяет:
  .py        — ast.parse (точная проверка интерпретатором);
  .json      — json.loads;
  .kt/.kts   — баланс скобок сканером, понимающим строки ("...", \"\"\"...\"\"\"),
               шаблоны ${...}, символьные литералы и комментарии (// и /* */,
               вложенные — как в Kotlin).

Bash: если команда скармливает Python'у heredoc (`python - <<'PY' … PY`),
тело heredoc проверяется ast.parse ДО запуска — оборванный или лишённый
отступов скрипт не выполнится. Проверяются только heredoc с кавычками у
маркера (<<'PY') — в них шелл ничего не подставляет, значит тело и есть
финальный Python; и только когда stdin читает сам python (`python -`),
а не скрипт с данными (`python script.py <<DATA`).

Философия fail-open: хук блокирует только УВЕРЕННО битую правку. Любая
внутренняя ошибка самого хука, неизвестное расширение, не найденный
old_string — пропуск без вердикта (инструмент Edit сам откажет, если что).
Ложная блокировка рабочей правки хуже пропущенной ошибки — CI всё равно
поймает, а вот встать колом посреди автономной фазы нельзя.
"""

from __future__ import annotations

import ast
import json
import re
import sys

CODE_SUFFIXES = (".py", ".json", ".kt", ".kts")

# `… python[3] -` в конце строки вызова: stdin — это программа, а не данные
PYTHON_STDIN_RE = re.compile(r"python[\w.]*\s+-?\s*$")
HEREDOC_RE = re.compile(r"<<(-?)\s*(['\"])(\w+)\2")


def extract_python_heredocs(command: str) -> list[tuple[str, int]]:
    """Найти тела heredoc, которые исполняет Python: [(тело, строка_начала)].

    Маркер `<<'TAG'`, встретившийся ВНУТРИ тела другого heredoc, — это просто
    текст (шелл его не видит), поэтому вложенные совпадения пропускаются:
    двигаемся по команде слева направо и перескакиваем через уже съеденные тела.
    """
    found = []
    consumed_until = 0  # позиция, до которой команда уже «съедена» телами heredoc
    for match in HEREDOC_RE.finditer(command):
        if match.start() < consumed_until:
            continue  # маркер внутри тела предыдущего heredoc — не шелл-уровень
        strip_tabs, tag = match.group(1) == "-", match.group(3)
        line_start = command.rfind("\n", 0, match.start()) + 1
        invocation = command[line_start:match.start()]
        body_start = command.find("\n", match.end())
        if body_start == -1:
            continue
        body_start += 1
        terminator = re.search(
            rf"^\t*{re.escape(tag)}\s*$", command[body_start:], re.MULTILINE
        )
        if terminator:
            body = command[body_start: body_start + terminator.start()]
            consumed_until = body_start + terminator.end()
        else:
            body = command[body_start:]
            consumed_until = len(command)
        if not PYTHON_STDIN_RE.search(invocation.strip()):
            continue  # heredoc не для python (или это данные) — тело уже съедено
        if strip_tabs:  # <<- : шелл срежет ведущие табы
            body = "\n".join(line.lstrip("\t") for line in body.split("\n"))
        heredoc_line = command.count("\n", 0, body_start) + 1
        found.append((body, heredoc_line))
    return found


def build_new_content(tool_name: str, tool_input: dict) -> tuple[str | None, str | None]:
    """Вернуть (путь, будущее содержимое) или (path, None) = «не судим»."""
    path = tool_input.get("file_path") or ""
    if not path.endswith(CODE_SUFFIXES):
        return path, None

    if tool_name == "Write":
        return path, tool_input.get("content")

    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        return path, None  # файла нет/не читается — пусть решает сам Edit

    if tool_name == "Edit":
        edits = [tool_input]
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
    else:
        return path, None

    current = source
    for edit in edits:
        old = edit.get("old_string") or ""
        new = edit.get("new_string") or ""
        if not old or old not in current:
            return path, None  # Edit сам вернёт ошибку «old_string не найден»
        count = -1 if edit.get("replace_all") else 1
        current = current.replace(old, new, count)
    return path, current


def check_python(text: str) -> str | None:
    try:
        ast.parse(text)
    except SyntaxError as error:
        return f"Python не парсится: строка {error.lineno}: {error.msg}"
    return None


def check_json(text: str) -> str | None:
    try:
        json.loads(text)
    except json.JSONDecodeError as error:
        return f"JSON не парсится: строка {error.lineno}: {error.msg}"
    return None


def check_kotlin(text: str) -> str | None:
    """Баланс скобок с учётом строк, шаблонов ${...} и комментариев."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[tuple[str, int]] = []  # (что открыто, строка)
    i, n, line = 0, len(text), 1

    def top() -> str | None:
        return stack[-1][0] if stack else None

    while i < n:
        char = text[i]
        if char == "\n":
            line += 1

        if top() == "raw":  # """…""" — без экранирования
            if text.startswith('"""', i):
                stack.pop()
                i += 3
            elif text.startswith("${", i):
                stack.append(("tmpl", line))
                i += 2
            else:
                i += 1
            continue

        if top() == "str":  # "…" — с экранированием
            if char == "\\":
                i += 2
            elif char == '"':
                stack.pop()
                i += 1
            elif text.startswith("${", i):
                stack.append(("tmpl", line))
                i += 2
            elif char == "\n":
                return f"строка {line}: незакрытая строка \""
            else:
                i += 1
            continue

        # режим кода
        if text.startswith("//", i):
            j = text.find("\n", i)
            if j == -1:
                break
            i = j
            continue
        if text.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    if text[i] == "\n":
                        line += 1
                    i += 1
            if depth:
                return f"незакрытый комментарий /* (открыт до конца файла)"
            continue
        if text.startswith('"""', i):
            stack.append(("raw", line))
            i += 3
            continue
        if char == '"':
            stack.append(("str", line))
            i += 1
            continue
        if char == "'":  # 'a', '\n', '￿'
            i += 1
            if i < n and text[i] == "\\":
                i += 2
                while i < n and text[i] not in ("'", "\n"):
                    i += 1
            else:
                i += 1
            if i < n and text[i] == "'":
                i += 1
            continue

        if char in "([{":
            stack.append((char, line))
        elif char in ")]}":
            if char == "}" and top() == "tmpl":
                stack.pop()  # закрылся шаблон — вернулись в строку
            elif top() == pairs[char]:
                stack.pop()
            else:
                return f"строка {line}: «{char}» без парной «{pairs[char]}»"
        i += 1

    unclosed = [item for item in stack if item[0] in "([{" or item[0] == "tmpl"]
    if unclosed:
        symbol, at_line = unclosed[0]
        shown = "${" if symbol == "tmpl" else symbol
        return f"«{shown}» со строки {at_line} не закрыта до конца файла"
    if stack:  # осталась незакрытая строка/raw-строка
        kind, at_line = stack[0]
        return f"незакрытая {'raw-' if kind == 'raw' else ''}строка со строки {at_line}"
    return None


def deny(path: str, reason: str) -> None:
    message = (
        f"ПРАВКА ЗАБЛОКИРОВАНА: после неё файл {path} перестаёт быть валидным. "
        f"{reason}. Похоже на обрыв содержимого или сбитые отступы — "
        f"перечитай файл и оформи правку заново, целиком и с правильными отступами."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": f"⛔ Хук-валидатор отклонил правку {path}: {reason}",
    }, ensure_ascii=False))


def deny_bash(reason: str) -> None:
    message = (
        f"КОМАНДА ЗАБЛОКИРОВАНА: Python в heredoc не парсится — {reason}. "
        f"Похоже на обрыв или потерянные отступы. Не чини heredoc: запиши скрипт "
        f"в файл .py через Write (его проверит этот же хук) и запусти короткой "
        f"командой `python3 путь/к/файлу.py` — так требует CLAUDE.md."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": f"⛔ Хук-валидатор отклонил Bash: битый Python в heredoc ({reason})",
    }, ensure_ascii=False))


def main() -> None:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        for body, line in extract_python_heredocs(command):
            problem = check_python(body)
            if problem:
                deny_bash(f"heredoc со строки {line} команды: {problem}")
                return
        return

    path, new_content = build_new_content(tool_name, tool_input)
    if new_content is None:
        return
    if path.endswith(".py"):
        problem = check_python(new_content)
    elif path.endswith(".json"):
        problem = check_json(new_content)
    else:
        problem = check_kotlin(new_content)
    if problem:
        deny(path, problem)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — fail-open: хук не должен стать блокером сам
        pass
