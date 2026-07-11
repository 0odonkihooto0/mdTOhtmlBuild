# mdTOhtmlBuild — нормативные документы СП → интерактивные HTML

Лаборатория контент-воронки [komplid.ru](https://komplid.ru): превращаем корпус
строительных нормативов (СП) из markdown в интерактивные HTML-страницы и готовим
сетку строительных калькуляторов — для SEO/AEO/GEO-трафика маркетинг-сайта.

## Структура

| Папка | Что это |
|---|---|
| `docs/` | Стратегия и планы внедрения: [00 — стратегия SEO/AEO/GEO + blindspot-реестр](docs/00-STRATEGY-SEO-AEO-GEO.md) · [01 — СП-страницы](docs/01-SP-PAGES-PLAN.md) · [02 — калькуляторы](docs/02-CALCULATORS-PLAN.md) |
| `normative-md/` | Корпус: 323 СП в markdown (конвертация Docling из PDF) + логи и манифест конвертации |
| `sp-builder/` | **Генератор** md → самодостаточный интерактивный HTML (Python 3.11, stdlib). См. [sp-builder/README.md](sp-builder/README.md) |
| `sp-html/` | **Весь корпус: 323 готовые интерактивные страницы** + картинки (JPEG из PDF) + `build-report.json` с метриками качества. Эталон с ручным оверлеем: [СП 48.13330.2019 «Организация строительства»](sp-html/sp-48-13330-2019.html). Упоминания других СП в текстах — рабочие кросс-ссылки внутри папки |
| `downloads_faufcc/` | Исходные PDF (324 шт.) — источник для восстановления картинок, выброшенных Docling'ом |
| `pdf-to-html/` | Ранний прототип конвертера (PDF-пайплайн, две темы). Дизайн-токены переехали в sp-builder |

## Быстрый старт

```bash
# один документ
python3 sp-builder/build.py "normative-md/SP_48.13330.2019_«СНиП 12-01-2004 Организация строительства».md"
# → sp-html/sp-48-13330-2019.html  (открыть в браузере)

# весь корпус одной командой: все .md из папки → HTML в папку
python3 sp-builder/build.py --all -i normative-md -o output
# → output/*.html + output/build-report.json (метрики качества по каждому документу)

# для восстановления картинок из PDF: pip install pymupdf (опционально)
```

## Связанные репозитории

- [komplid-marketing](https://github.com/0odonkihooto0/komplid-marketing) — маркетинг-сайт (Next.js), куда интегрируются страницы и калькуляторы
- [Komplid2](https://github.com/0odonkihooto0/Komplid2) — SaaS-приложение (app.komplid.ru)
- [plannotator/effective-html](https://github.com/plannotator/effective-html) — идейная база формата «один самодостаточный HTML»
