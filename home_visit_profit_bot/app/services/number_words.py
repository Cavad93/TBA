"""Числа прописью → цифрами (Фаза 14.5), до геокодинга.

Системный распознаватель телефона обычно отдаёт цифры, а наш ASR на сервере 2 —
прописью: «улица ленина сорок» вместо «улица ленина 40». Геокодер ждёт цифры, поэтому
нормализуем: «сорок» → «40», «сто двадцать три» → «123». Диапазон домов — до 999,
этого адресам хватает; составные числа собираются (сотни > десятки > единицы).

Правило склейки: в одном числе разряды строго УБЫВАЮТ. Если новое числительное того
же или большего разряда — это уже следующее число («сорок сорок» → «40 40», не «80»).
Только целые неотрицательные; не-числовые слова не трогаем, пробелы сохраняем.
"""

from __future__ import annotations

import re

_UNITS = {
    "ноль": 0, "один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
    "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
    "девятнадцать": 19,
}
_TENS = {
    "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
}
_HUNDREDS = {
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500,
    "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
}
_ALL = {**_UNITS, **_TENS, **_HUNDREDS}


def _rank(value: int) -> int:
    return 3 if value >= 100 else (2 if value >= 20 else 1)


def words_to_number(text: str) -> str:
    """Заменить последовательности числительных на цифры. Прочее — без изменений."""
    if not text:
        return text
    tokens = re.split(r"(\s+)", text)
    out: list[str] = []
    current = 0
    last_rank: int | None = None
    have = False
    pending_space = ""

    def flush() -> None:
        nonlocal current, last_rank, have, pending_space
        if have:
            out.append(str(current))
        current = 0
        last_rank = None
        have = False

    for token in tokens:
        if token.strip() == "":
            if have:
                pending_space = token  # пробел внутри/после числа — придержим
            else:
                out.append(token)
            continue
        word = token.lower()
        if word in _ALL:
            value = _ALL[word]
            rank = _rank(value)
            if have and last_rank is not None and rank >= last_rank:
                # Новое число: закрываем прежнее и возвращаем разделитель между ними.
                flush()
                if pending_space:
                    out.append(pending_space)
            pending_space = ""
            current += value
            last_rank = rank
            have = True
        else:
            flush()
            if pending_space:
                out.append(pending_space)
                pending_space = ""
            out.append(token)
    flush()
    if pending_space:
        out.append(pending_space)
    return "".join(out)
