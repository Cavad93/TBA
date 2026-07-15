#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор блога «Визиторкрута».

Читает статьи-модули из articles/*.py (каждый определяет словарь ARTICLE),
рендерит index-страницу блога с группировкой и по одной HTML-странице на
статью, используя общий шаблон (шапка, «хлебные крошки», тело .prose, блок
«ключевых фактов», связанные статьи, нижний CTA, подвал).

Запуск:  python3 home_visit_profit_bot/deploy/blog_build/build.py
Вывод:   home_visit_profit_bot/deploy/site/blog/*.html
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "articles"
OUT_DIR = ROOT.parent / "site" / "blog"

# Порядок групп в оглавлении блога.
GROUP_ORDER = [
    "Главное решение",
    "Дорога и деньги",
    "Нагрузка и режим",
    "Учёт и отчёты",
    "Адреса и навигация",
    "Настройки и приватность",
]

# Набор иконок (внутренность <svg>). Ключ = поле "icon" статьи.
ICONS = {
    "verdict": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "gauge": '<path d="M12 14a2 2 0 1 0-2-2"/><path d="M4.9 19a10 10 0 1 1 14.2 0"/><path d="m13.4 10.6 3.6-3.6"/>',
    "ruble": '<path d="M6 11h8a4 4 0 0 0 0-8H8v14"/><path d="M6 15h6"/>',
    "car": '<path d="M5 17h14"/><path d="M4 12l2-5a2 2 0 0 1 2-1h8a2 2 0 0 1 2 1l2 5v4a1 1 0 0 1-1 1h-1a2 2 0 0 1-4 0H8a2 2 0 0 1-4 0H3a1 1 0 0 1-1-1v-4Z"/><circle cx="7.5" cy="16.5" r="1.5"/><circle cx="16.5" cy="16.5" r="1.5"/>',
    "route": '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/><path d="M9 19h6a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6"/>',
    "parking": '<rect width="18" height="18" x="3" y="3" rx="3"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/>',
    "indices": '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/>',
    "baseline": '<path d="M3 12h4l2-7 3 14 2-9 2 4h5"/>',
    "overwork": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "gps": '<circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.4 8 12 8 12s8-6.6 8-12a8 8 0 0 0-8-8Z"/>',
    "ledger": '<path d="M4 4a2 2 0 0 1 2-2h11a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2Z"/><path d="M8 7h6M8 11h6M8 15h4"/>',
    "wizard": '<path d="M12 3v2M12 19v2M5 12H3M21 12h-2"/><path d="m8 8 8 8M16 8 8 16"/><circle cx="12" cy="12" r="3"/>',
    "reports": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "address": '<path d="m21 21-4.3-4.3"/><circle cx="11" cy="11" r="7"/><path d="M11 8v6M8 11h6"/>',
    "nav": '<path d="m3 11 19-9-9 19-2-8-8-2Z"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15H4a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 6 8l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 12 4.6V4a2 2 0 1 1 4 0v.09A1.65 1.65 0 0 0 19 6l.06-.06a2 2 0 1 1 2.83 2.83L21.4 8A1.65 1.65 0 0 0 21 12h.09"/>',
    "feedback": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"/>',
    "privacy": '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "retention": '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6M14 11v6"/>',
}


def load_articles():
    mods = []
    for path in sorted(ARTICLES_DIR.glob("*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "ARTICLE"):
            print(f"! пропущен {path.name}: нет ARTICLE", file=sys.stderr)
            continue
        mods.append(mod.ARTICLE)
    mods.sort(key=lambda a: a["num"])
    return mods


def icon_svg(key, cls="icon"):
    inner = ICONS.get(key, ICONS["verdict"])
    return f'<svg class="{cls}" viewBox="0 0 24 24">{inner}</svg>'


def head(title, description, css_extra=""):
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="/ds.css">
<link rel="stylesheet" href="/blog.css">{css_extra}
</head>
<body>"""


HEADER = """
  <header class="site-header">
    <div class="wrap">
      <a class="wordmark" href="/">Визиторкрут</a>
      <nav class="site-nav">
        <a class="nav-hide" href="/#how">Как работает</a>
        <a class="nav-hide" href="/#features">Возможности</a>
        <a href="/blog/">Блог</a>
        <a class="nav-cta" href="/vizitorkrut.apk" download>Скачать</a>
      </nav>
    </div>
  </header>
"""

FOOTER = """
  <footer class="site-footer">
    <div class="wrap">
      <div class="footer-cols">
        <div>
          <h4>Визиторкрут</h4>
          <ul>
            <li><a href="/">Главная</a></li>
            <li><a href="/blog/">Блог о возможностях</a></li>
            <li><a href="/vizitorkrut.apk" download>Скачать приложение</a></li>
          </ul>
        </div>
        <div>
          <h4>Документы</h4>
          <ul>
            <li><a href="/policy.html">Политика обработки ПДн</a></li>
            <li><a href="/consent.html">Согласие на обработку</a></li>
          </ul>
        </div>
        <div>
          <h4>Контакты</h4>
          <ul>
            <li><a href="mailto:support@vizitorkrut.ru">support@vizitorkrut.ru</a></li>
          </ul>
        </div>
      </div>
      © 2026 Визиторкрут · Навигатор показывает, куда ехать. Приложение — стоит ли.
    </div>
  </footer>
"""

CTA_BAND = """
      <div class="cta-band">
        <h2>Проверь любой заказ за секунду</h2>
        <p>Установи приложение и посмотри честный вердикт по своему следующему адресу — стоит ехать или нет.</p>
        <a class="btn-primary" href="/vizitorkrut.apk" download>Скачать для Android</a>
        <span class="cta-note">Android 8+ · установка из файла · бесплатно</span>
      </div>
"""


def render_article(art, by_slug):
    facts = "\n".join(f"          <li>{f}</li>" for f in art.get("keyfacts", []))
    facts_block = ""
    if facts:
        ftitle = art.get("keyfacts_title", "Как это устроено под капотом")
        facts_block = f"""
      <div class="keyfacts" style="margin-top:var(--space-12)">
        <h3>{icon_svg('settings')} {ftitle}</h3>
        <ul>
{facts}
        </ul>
      </div>"""

    related_cards = ""
    rel = [by_slug[s] for s in art.get("related", []) if s in by_slug]
    if rel:
        items = ""
        for r in rel:
            items += f"""
        <a class="article-card" href="/blog/{r['slug']}.html">
          <div class="ficon">{icon_svg(r['icon'])}</div>
          <h3>{r['title']}</h3>
          <p>{r['dek']}</p>
          <div class="meta"><span class="arrow">Читать →</span></div>
        </a>"""
        related_cards = f"""
    <section class="related">
      <div class="wrap">
        <h2>Читать дальше</h2>
        <div class="card-grid">{items}
        </div>
      </div>
    </section>"""

    title = f"{art['title']} — Визиторкрут"
    html = head(title, art["dek"])
    html += HEADER
    html += f"""
  <main>
    <article>
      <div class="article-head">
        <div class="wrap-narrow">
          <nav class="breadcrumb"><a href="/">Главная</a> · <a href="/blog/">Блог</a> · {art['category']}</nav>
          <span class="cat-chip">{art['category']}</span>
          <h1>{art['title']}</h1>
          <p class="dek">{art['dek']}</p>
          <div class="article-meta">
            <span>Функция №{art['num']:02d}</span>
            <span>{art.get('reading', 4)} мин чтения</span>
          </div>
        </div>
      </div>

      <div class="wrap-narrow">
        <div class="prose">
{art['body']}
        </div>
{facts_block}
      </div>
{CTA_BAND_WRAPPED}
    </article>
{related_cards}
  </main>
{FOOTER}
</body>
</html>"""
    return html


CTA_BAND_WRAPPED = f"""
      <div class="wrap-narrow">{CTA_BAND}
      </div>"""


def render_index(articles):
    html = head(
        "Блог Визиторкрута — все возможности приложения",
        "Разбор каждой функции приложения «Визиторкрут»: что делает, как устроено и зачем нужно выездному работнику. Вердикт по заказу, расчёт ₽/час, маршруты, парковка, нагрузка и приватность.",
    )
    html += HEADER
    html += """
  <main>
    <section class="blog-hero">
      <div class="wrap">
        <h1>Как работает Визиторкрут — по одной функции за раз</h1>
        <p>Каждая статья — про одну возможность приложения: что она делает, как устроена внутри и какую боль выездного работника закрывает. Начните с «Главного решения», а дальше — по интересу.</p>
      </div>
    </section>
    <section class="block" style="border-top:none;padding-top:0">
      <div class="wrap">"""

    groups = {}
    for a in articles:
        groups.setdefault(a["group"], []).append(a)

    ordered = [g for g in GROUP_ORDER if g in groups] + [g for g in groups if g not in GROUP_ORDER]
    for g in ordered:
        html += f'\n        <h2 class="blog-group-title">{g}</h2>\n        <div class="card-grid">'
        for a in sorted(groups[g], key=lambda x: x["num"]):
            html += f"""
          <a class="article-card" href="/blog/{a['slug']}.html">
            <div class="ficon">{icon_svg(a['icon'])}</div>
            <span class="num">Функция №{a['num']:02d}</span>
            <h3>{a['title']}</h3>
            <p>{a['dek']}</p>
            <div class="meta"><span class="arrow">Читать →</span><span>· {a.get('reading',4)} мин</span></div>
          </a>"""
        html += "\n        </div>"

    html += f"""
      </div>
    </section>
    <div class="wrap">{CTA_BAND}
    </div>
  </main>
{FOOTER}
</body>
</html>"""
    return html


def main():
    articles = load_articles()
    if not articles:
        print("Нет статей — нечего собирать.", file=sys.stderr)
        return 1
    by_slug = {a["slug"]: a for a in articles}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "index.html").write_text(render_index(articles), encoding="utf-8")
    for a in articles:
        (OUT_DIR / f"{a['slug']}.html").write_text(render_article(a, by_slug), encoding="utf-8")

    print(f"Собрано: index.html + {len(articles)} статей → {OUT_DIR}")
    for a in articles:
        print(f"  {a['num']:02d}  {a['slug']:22s}  {a['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
