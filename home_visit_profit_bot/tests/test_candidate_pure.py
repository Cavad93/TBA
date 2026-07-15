"""Золотые векторы выгодности (Фаза 3.1): чистое ядро совпадает с фикстурами.

Тот же файл tests/golden/candidate_vectors.json гоняет Kotlin-CI. Если этот тест
падает после правки формулы — надо перегенерировать векторы (python -m
scripts.gen_golden_vectors) И обновить Kotlin-калькулятор, иначе телефон и сервер
разойдутся. В этом весь смысл: расхождение ловится тестом, а не в бою.
"""
from __future__ import annotations

import json
import os

import pytest

from app.services.candidate_pure import evaluate

_VECTORS_PATH = os.path.join(os.path.dirname(__file__), "golden", "candidate_vectors.json")


def _load():
    with open(_VECTORS_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def test_vectors_file_exists_and_nonempty():
    vectors = _load()
    assert len(vectors) >= 5
    # Контракт покрывает все три вердикта.
    verdicts = {v["expected"]["verdict"] for v in vectors}
    assert {"go", "edge", "skip"} <= verdicts


@pytest.mark.parametrize("vector", _load(), ids=[v["name"] for v in _load()])
def test_pure_matches_golden(vector):
    assert evaluate(vector["inputs"]) == vector["expected"]
