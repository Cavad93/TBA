#!/usr/bin/env python3
"""PreToolUse-хук: не пропускать Edit/Write, ломающие синтаксис файла.

Строит содержимое файла, каким оно станет ПОСЛЕ правки, и проверяет:
  .py        — ast.parse (точная проверка интерпретатором);
  .json      — json.loads;
  .kt/.kts   — баланс скобок сканером, понимающим строки ("...", \"\"\"...\"\"\"),
               шаблоны ${...}, символьные литералы и комментарии (// и /* */,
               вложенные — как в Kotlin).

Философия fail-open: хук блокирует только УВЕРЕННО битую правку. Любая
внутренняя ошибка самого хука, неизвестное расширение, не найденный
old_string — пропуск без вердикта (инструмент Edit сам откажет, если что).
Ложная блокировка рабочей правки хуже пропущенной ошибки — CI всё равно
поймает, а вот встать колом посреди автономной фазы нельзя.
"""

from __future__ import annotations

import ast
import json
import sys

CODE_SUFFIXES = (".py", ".json", ".kt", ".kts")


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


def main() -> None:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
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
