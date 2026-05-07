# Judge Model Comparison — Experiment Log

Цель: сравнить качество работы LLMJudge на разных моделях и температурах.
Датасет: 14 кейсов (`cases.json`), 12 критериев (compliance / sales / knowledge).
Метрика: `total_score` (0–100), delta vs baseline, criterion_agreement.

Скрипты:
- `run_compare.py` — прогон модели, запись результата в JSON
- `compare_report.py` — сравнение нескольких JSON с baseline

---

## Baseline — openai/gpt-4o-mini

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | openai/gpt-4o-mini |
| Temperature | default |
| Кейсов | 14/14 |
| Время | 43 с |
| Mean score | **62.7** |

### Результаты по кейсам

| case_id | score |
|---|---|
| compliance_greeting_bank_word | 72.2 |
| compliance_post_answer_time_request | 83.3 |
| compliance_early_qualification | 38.9 |
| compliance_novoreg_missing_congrats | 44.4 |
| sales_no_empathy_or_joining | 66.7 |
| sales_closed_questions_chain | 50.0 |
| sales_no_summarizing | 44.4 |
| knowledge_wrong_tariff_price | 27.8 |
| knowledge_wrong_limits | 50.0 |
| knowledge_wrong_sanctions | 55.6 |
| knowledge_wrong_currency | 94.4 |
| escalation_tax_consultation | 55.6 |
| strong_perfect_novoreg | 100.0 |
| strong_perfect_skeptic | 94.4 |

Файл результатов: `results/ideal.json`

---

---

## Эксперимент 1 — meta-llama/llama-3.1-8b-instruct

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | meta-llama/llama-3.1-8b-instruct |
| Temperature | default |
| Кейсов | 14/14 запущено, **0/14 успешно** |
| Время | 65 с |
| Mean score | 0.0 |

**Результат: FAIL — модель не пригодна для использования с судьёй.**

Все кейсы упали с ошибкой `Compliance parsing failed`. Модель возвращает JSON обёрнутым в `{"name": "ComplianceLlmOutput", "parameters": {...}}` вместо плоской схемы, которую ожидает Pydantic. 8B-модели, как правило, не поддерживают structured output / tool calling на уровне, достаточном для судьи.

**Вывод:** судья требует поддержки structured output. Модели без надёжного tool calling непригодны.

Файл результатов: `results/llama3_8b.json`

---

---

## Эксперимент 2 — qwen/qwen3-32b

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | qwen/qwen3-32b |
| Temperature | default |
| Кейсов | 14/14 успешно |
| Время | 121 с |
| Mean score | **62.3** (delta vs baseline: **−0.4**) |
| Criterion agreement | **84.5%** |

**Результат: модель работает, средний балл практически совпадает с baseline.**

### Результаты по кейсам

| case_id | ideal | qwen3-32b | Δ |
|---|---|---|---|
| compliance_greeting_bank_word | 72.2 | 72.2 | 0.0 |
| compliance_post_answer_time_request | 83.3 | 55.6 | −27.8 |
| compliance_early_qualification | 38.9 | 55.6 | +16.7 |
| compliance_novoreg_missing_congrats | 44.4 | 16.7 | −27.8 |
| sales_no_empathy_or_joining | 66.7 | 72.2 | +5.6 |
| sales_closed_questions_chain | 50.0 | 55.6 | +5.6 |
| sales_no_summarizing | 44.4 | 77.8 | +33.3 |
| knowledge_wrong_tariff_price | 27.8 | 50.0 | +22.2 |
| knowledge_wrong_limits | 50.0 | 72.2 | +22.2 |
| knowledge_wrong_sanctions | 55.6 | 44.4 | −11.1 |
| knowledge_wrong_currency | 94.4 | 61.1 | −33.3 |
| escalation_tax_consultation | 55.6 | 50.0 | −5.6 |
| strong_perfect_novoreg | 100.0 | 100.0 | 0.0 |
| strong_perfect_skeptic | 94.4 | 88.9 | −5.6 |

### Согласованность по критериям

| Критерий | ideal% | qwen3-32b% | agreement |
|---|---|---|---|
| compliance.greeting_ozon | 100% | 100% | 100% |
| compliance.post_answer_time_requests | 93% | 93% | 100% |
| compliance.forbidden_qualification | 71% | 79% | 79% |
| compliance.novoreg_scenario | 43% | 21% | 79% |
| compliance.escalation | 93% | 86% | 79% |
| compliance.stop_words | 43% | 43% | 100% |
| sales.empathy_joining | 57% | 43% | 71% |
| sales.question_format_open_alternative | 29% | 21% | 79% |
| sales.summarizing | 57% | 50% | 64% |
| knowledge.tariff_accuracy | 71% | 79% | 93% |
| knowledge.limits_commissions_accuracy | 71% | 79% | 93% |
| knowledge.objection_handling | 57% | 79% | 79% |

**Наблюдения:**
- Средний балл почти идентичен baseline (62.3 vs 62.7), но на уровне кейсов — значительные расхождения (до ±33)
- Слабее всего совпадает `sales.summarizing` (64%) и `sales.empathy_joining` (71%)
- `knowledge.*` критерии — хорошее совпадение (93%)
- Модель строже в knowledge, мягче в compliance/sales
- В 2 раза медленнее baseline (121с vs 43с)

Файл результатов: `results/qwen3_32b.json`

---

---

## Эксперимент 3 — openai/gpt-4o-mini, temperature=0.0

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | openai/gpt-4o-mini |
| Temperature | 0.0 |
| Кейсов | 14/14 успешно |
| Время | 42 с |
| Mean score | **65.9** (delta vs baseline: **+3.2**) |
| Criterion agreement | **89.9%** |

**Результат: выше baseline по среднему, но с заметными расхождениями на отдельных кейсах.**

### Результаты по кейсам

| case_id | ideal | t=0.0 | Δ |
|---|---|---|---|
| compliance_greeting_bank_word | 72.2 | 72.2 | 0.0 |
| compliance_post_answer_time_request | 83.3 | 83.3 | 0.0 |
| compliance_early_qualification | 38.9 | 50.0 | +11.1 |
| compliance_novoreg_missing_congrats | 44.4 | 88.9 | +44.4 |
| sales_no_empathy_or_joining | 66.7 | 55.6 | −11.1 |
| sales_closed_questions_chain | 50.0 | 50.0 | 0.0 |
| sales_no_summarizing | 44.4 | 44.4 | 0.0 |
| knowledge_wrong_tariff_price | 27.8 | 61.1 | +33.3 |
| knowledge_wrong_limits | 50.0 | 55.6 | +5.6 |
| knowledge_wrong_sanctions | 55.6 | 61.1 | +5.6 |
| knowledge_wrong_currency | 94.4 | 61.1 | −33.3 |
| escalation_tax_consultation | 55.6 | 44.4 | −11.1 |
| strong_perfect_novoreg | 100.0 | 100.0 | 0.0 |
| strong_perfect_skeptic | 94.4 | 94.4 | 0.0 |

### Согласованность по критериям

| Критерий | ideal% | t=0.0% | agreement |
|---|---|---|---|
| compliance.greeting_ozon | 100% | 100% | 100% |
| compliance.post_answer_time_requests | 93% | 93% | 100% |
| compliance.forbidden_qualification | 71% | 71% | 100% |
| compliance.novoreg_scenario | 43% | 29% | 86% |
| compliance.escalation | 93% | 93% | 100% |
| compliance.stop_words | 43% | 43% | 100% |
| sales.empathy_joining | 57% | 57% | 86% |
| sales.question_format_open_alternative | 29% | 36% | 79% |
| sales.summarizing | 57% | 57% | 71% |
| knowledge.tariff_accuracy | 71% | 79% | 93% |
| knowledge.limits_commissions_accuracy | 71% | 79% | 93% |
| knowledge.objection_handling | 57% | 71% | 71% |

**Наблюдения:**
- Criterion agreement выше, чем у qwen3-32b (89.9% vs 84.5%) — та же модель, другая температура
- Крупные расхождения: `compliance_novoreg_missing_congrats` (+44.4) и `knowledge_wrong_currency` (−33.3) — модель нестабильна в пограничных сценариях даже при t=0.0
- Скорость идентична baseline (42с)

Файл результатов: `results/gpt4o_mini_t0.json`

---

---

## Эксперимент 4 — openai/gpt-4o-mini, temperature=1.0

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | openai/gpt-4o-mini |
| Temperature | 1.0 |
| Кейсов | 14/14 успешно |
| Время | 47 с |
| Mean score | **64.7** (delta vs baseline: **+2.0**) |
| Criterion agreement | **91.1%** |

**Результат: неожиданно — t=1.0 показал более высокое criterion agreement, чем t=0.0 (91.1% vs 89.9%).**

### Результаты по кейсам

| case_id | ideal | t=1.0 | Δ |
|---|---|---|---|
| compliance_greeting_bank_word | 72.2 | 72.2 | 0.0 |
| compliance_post_answer_time_request | 83.3 | 83.3 | 0.0 |
| compliance_early_qualification | 38.9 | 38.9 | 0.0 |
| compliance_novoreg_missing_congrats | 44.4 | 77.8 | +33.3 |
| sales_no_empathy_or_joining | 66.7 | 66.7 | 0.0 |
| sales_closed_questions_chain | 50.0 | 44.4 | −5.6 |
| sales_no_summarizing | 44.4 | 55.6 | +11.1 |
| knowledge_wrong_tariff_price | 27.8 | 61.1 | +33.3 |
| knowledge_wrong_limits | 50.0 | 44.4 | −5.6 |
| knowledge_wrong_sanctions | 55.6 | 50.0 | −5.6 |
| knowledge_wrong_currency | 94.4 | 61.1 | −33.3 |
| escalation_tax_consultation | 55.6 | 55.6 | 0.0 |
| strong_perfect_novoreg | 100.0 | 100.0 | 0.0 |
| strong_perfect_skeptic | 94.4 | 94.4 | 0.0 |

### Согласованность по критериям

| Критерий | ideal% | t=1.0% | agreement |
|---|---|---|---|
| compliance.greeting_ozon | 100% | 100% | 100% |
| compliance.post_answer_time_requests | 93% | 93% | 100% |
| compliance.forbidden_qualification | 71% | 71% | 100% |
| compliance.novoreg_scenario | 43% | 21% | 79% |
| compliance.escalation | 93% | 93% | 100% |
| compliance.stop_words | 43% | 43% | 100% |
| sales.empathy_joining | 57% | 57% | 86% |
| sales.question_format_open_alternative | 29% | 36% | 79% |
| sales.summarizing | 57% | 64% | 79% |
| knowledge.tariff_accuracy | 71% | 86% | 86% |
| knowledge.limits_commissions_accuracy | 71% | 79% | 93% |
| knowledge.objection_handling | 57% | 50% | 93% |

**Наблюдения:**
- `knowledge_wrong_currency` стабильно отклоняется во всех прогонах (−33.3) — возможно, пограничный кейс требует пересмотра
- `compliance_novoreg_missing_congrats` и `knowledge_wrong_tariff_price` систематически завышены относительно baseline (+33–44) при любой температуре
- Температура не оказывает значимого влияния на criterion agreement для gpt-4o-mini

Файл результатов: `results/gpt4o_mini_t1.json`

---

## Сводная таблица всех прогонов

| Модель | Temp | Mean score | Δ vs ideal | Crit. agree | Время | Статус |
|---|---|---|---|---|---|---|
| openai/gpt-4o-mini | default | 62.7 | — | — | 43 с | baseline |
| meta-llama/llama-3.1-8b-instruct | default | 0.0 | −62.7 | n/a | 65 с | FAIL (no structured output) |
| qwen/qwen3-32b | default | 62.3 | −0.4 | 84.5% | 121 с | OK |
| openai/gpt-4o-mini | 0.0 | 65.9 | +3.2 | 89.9% | 42 с | OK |
| openai/gpt-4o-mini | 1.0 | 64.7 | +2.0 | 91.1% | 47 с | OK |

---

---

## Эксперимент 5 — qwen/qwen-2.5-72b-instruct

| Параметр | Значение |
|---|---|
| Дата | 2026-05-07 |
| Модель | qwen/qwen-2.5-72b-instruct |
| Temperature | default |
| Кейсов | 14/14 запущено, 1 с parsing error |
| Время | 148 с |
| Mean score | **56.8** (delta vs baseline: **−6.0**) |
| Criterion agreement | **79.2%** |

**Результат: хуже qwen3-32b и baseline. 1 кейс упал с `Knowledge parsing failed` (compliance_greeting_bank_word → score=0.0).**

### Результаты по кейсам

| case_id | ideal | qwen2.5-72b | Δ |
|---|---|---|---|
| compliance_greeting_bank_word | 72.2 | 0.0 | −72.2 ⚠️ (parsing error) |
| compliance_post_answer_time_request | 83.3 | 77.8 | −5.6 |
| compliance_early_qualification | 38.9 | 44.4 | +5.6 |
| compliance_novoreg_missing_congrats | 44.4 | 44.4 | 0.0 |
| sales_no_empathy_or_joining | 66.7 | 50.0 | −16.7 |
| sales_closed_questions_chain | 50.0 | 50.0 | 0.0 |
| sales_no_summarizing | 44.4 | 55.6 | +11.1 |
| knowledge_wrong_tariff_price | 27.8 | 61.1 | +33.3 |
| knowledge_wrong_limits | 50.0 | 44.4 | −5.6 |
| knowledge_wrong_sanctions | 55.6 | 55.6 | 0.0 |
| knowledge_wrong_currency | 94.4 | 77.8 | −16.7 |
| escalation_tax_consultation | 55.6 | 50.0 | −5.6 |
| strong_perfect_novoreg | 100.0 | 100.0 | 0.0 |
| strong_perfect_skeptic | 94.4 | 83.3 | −11.1 |

### Согласованность по критериям

| Критерий | ideal% | qwen2.5-72b% | agreement |
|---|---|---|---|
| compliance.greeting_ozon | 100% | 93% | 93% |
| compliance.post_answer_time_requests | 93% | 86% | 93% |
| compliance.forbidden_qualification | 71% | 86% | 79% |
| compliance.novoreg_scenario | 43% | 36% | 71% |
| compliance.escalation | 93% | 79% | 71% |
| compliance.stop_words | 43% | 43% | 93% |
| sales.empathy_joining | 57% | 43% | 71% |
| sales.question_format_open_alternative | 29% | 21% | 86% |
| sales.summarizing | 57% | 36% | 64% |
| knowledge.tariff_accuracy | 71% | 57% | 86% |
| knowledge.limits_commissions_accuracy | 71% | 64% | 79% |
| knowledge.objection_handling | 57% | 79% | 64% |

**Наблюдения:**
- Несмотря на больший размер (72B > 32B), qwen2.5-72b хуже qwen3-32b по всем метрикам
- Периодические parsing errors — модель нестабильна в structured output
- Самое слабое место: `sales.summarizing` (64% agreement) и `compliance.escalation` (71%)
- В 3.5× медленнее baseline (148с vs 43с)

Файл результатов: `results/qwen2_5_72b.json`

---

## Итоговая сводная таблица

| Модель | Temp | Mean score | Δ vs ideal | Crit. agree | Время | Статус |
|---|---|---|---|---|---|---|
| openai/gpt-4o-mini | default | 62.7 | — | — | 43 с | **baseline** |
| openai/gpt-4o-mini | 0.0 | 65.9 | +3.2 | 89.9% | 42 с | OK |
| openai/gpt-4o-mini | 1.0 | 64.7 | +2.0 | 91.1% | 47 с | OK |
| qwen/qwen3-32b | default | 62.3 | −0.4 | 84.5% | 121 с | OK |
| qwen/qwen-2.5-72b-instruct | default | 56.8 | −6.0 | 79.2% | 148 с | OK (1 parsing error) |
| meta-llama/llama-3.1-8b-instruct | default | 0.0 | −62.7 | n/a | 65 с | **FAIL** |

## Общие выводы

1. **gpt-4o-mini — оптимальный выбор** для судьи: лучшее criterion agreement, самый быстрый, стабильный structured output
2. **Температура не критична** для gpt-4o-mini: разница между t=0.0 и t=1.0 незначительна (89.9% vs 91.1%)
3. **qwen3-32b — приемлемая альтернатива**: mean score почти идентичен baseline, но в 3× медленнее
4. **Больший размер ≠ лучше**: qwen2.5-72b хуже qwen3-32b, несмотря на размер
5. **Structured output — жёсткое требование**: модели без надёжного tool calling (8B и ниже) не пригодны
6. **Систематически нестабильные кейсы**: `knowledge_wrong_tariff_price` и `knowledge_wrong_currency` отклоняются во всех прогонах — требуют пересмотра ground truth
