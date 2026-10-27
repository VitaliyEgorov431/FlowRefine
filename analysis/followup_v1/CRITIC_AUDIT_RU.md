# Описательный аудит визуального критика

Это воспроизводимый разбор сохранённого текста, а не независимая, слепая или человеческая оценка. Извлекаются соседние буквальные упоминания полных названий узлов. Только явное 'connected with'/'begins with' без условной/неоднозначной конструкции считается проверяемым утверждением о направлении связи. Остальное помечается uncertain; искажённые названия и неявные пропуски не разрешаются догадками. Поэтому счётчики не являются precision/recall всего критика. Подписи ветвей автоматически не оцениваются.

Каждое утверждение сверяется отдельно с B0 (верность описания изображения) и эталоном/заданием (требуемая структура). Реальное ошибочное ребро B0 может быть верно описано критиком. Описание ребра само по себе не означает диагностику ошибки или рекомендацию исправить её. Изменения редактора приводятся отдельно и не доказывают причинное влияние отдельной фразы.

## test_chain_01

Источники: `runs/test_v1/test_chain_01/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Parcel workflow begins with Receiver parcel connected with Wrought parcel which is then connected with Attach shipping label which is further connected with Dispatch parcel. Attach shipping label is connected with both Parcel workflow complete and Print shipping label which is then connected with both Parcel workflow and Dispatch parcel.

Кандидатные утверждения: {'uncertain': 5, 'supported_by_B0': 1}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Пересказ с искажёнными Receiver/Wrought parcel. Фраза 'Attach shipping label is connected with both Parcel workflow complete and Print shipping label' при буквальном чтении описывает две связи, отсутствующие в B0 и задании. Рекомендации исправить конкретную ошибку нет; OCR-переходы неоднозначны.

- «Parcel workflow begins with Receiver parcel connected with Wrought parcel which is then connected with Attach shipping label»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Attach shipping label which is further connected with Dispatch parcel»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Dispatch parcel. Attach shipping label»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Attach shipping label is connected with both Parcel workflow complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Parcel workflow complete and Print shipping label»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Print shipping label which is then connected with both Parcel workflow and Dispatch parcel»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 0.8571428571428571 / 0.

## test_chain_02

Источники: `runs/test_v1/test_chain_02/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Backup begins with Select Files which is then connected with Create archive which is then connected with Upload archive which is finally connected with Record backup location which is finally connected with Backup complete.

Кандидатные утверждения: {'supported_by_B0': 4, 'contradicted_by_B0': 1}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Пересказ большей части цепочки, но Create archive → Upload archive не является прямым ребром B0/задания: между ними Encrypt archive. Это ошибочное описание, а не подтверждённая диагностика недостатка схемы. Явного предложения исправления нет.

- «Backup begins with Select Files»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Select Files which is then connected with Create archive»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Create archive which is then connected with Upload archive»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Upload archive which is finally connected with Record backup location»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Record backup location which is finally connected with Backup complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_chain_03

Источники: `runs/test_v1/test_chain_03/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Library intake begins with Receive donated book which is then connected with Inspect book which is then connected with Assign catalogue number which is further connected with Attach shelf label which is finally connected with Place book on shelf which is finally connected with Library intake complete.

Кандидатные утверждения: {'supported_by_B0': 6}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Пересказ всех шести последовательных связей согласуется с B0 и заданием. Ошибка или рекомендация не заявлена; точное описание правильной схемы само по себе не создаёт основания для изменения.

- «Library intake begins with Receive donated book»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Receive donated book which is then connected with Inspect book»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Inspect book which is then connected with Assign catalogue number»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Assign catalogue number which is further connected with Attach shelf label»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Attach shelf label which is finally connected with Place book on shelf»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Place book on shelf which is finally connected with Library intake complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_chain_04

Источники: `runs/test_v1/test_chain_04/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Experiment begins with Prepare sample which is then connected with Calibrate sensor which is then connected with Measure sample which is further connected with Save measurements which is finally connected with Clean equipment. Clean equipment is connected with Experiment complete which is finally connected with Measure sample.

Кандидатные утверждения: {'supported_by_B0': 6, 'uncertain': 1, 'contradicted_by_B0': 1}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Большая часть цепочки описана верно. Последнее утверждение Experiment complete → Measure sample противоречит B0 и заданию: у конечного узла нет такого исходящего ребра. Предложения исправить реальную ошибку нет.

- «Experiment begins with Prepare sample»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Prepare sample which is then connected with Calibrate sensor»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Calibrate sensor which is then connected with Measure sample»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Measure sample which is further connected with Save measurements»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Save measurements which is finally connected with Clean equipment»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Clean equipment. Clean equipment»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Clean equipment is connected with Experiment complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Experiment complete which is finally connected with Measure sample»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 0.7692307692307692 / 0.

## test_chain_05

Источники: `runs/test_v1/test_chain_05/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Podcast workflow begins with Record Interview which is then connected with Edit recording which is then connected with Normale audio which is further connected with Export Episode which is finally connected with Podcast workflow complete. Export Episode is connected with Publish episode which is then connected with Podcast workflow complete which is finally connected with Podcast workflow.

Кандидатные утверждения: {'supported_by_B0': 4, 'uncertain': 2, 'contradicted_by_B0': 1}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Пересказ с Normale audio и усечённым Podcast workflow; эти имена неоднозначны. Прямое Export Episode → Podcast workflow complete ошибочно: B0 и задание требуют промежуточный Publish episode. Позже верная последовательность через Publish episode тоже упомянута. Явной диагностики нет.

- «Podcast workflow begins with Record Interview»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Record Interview which is then connected with Edit recording»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Edit recording which is then connected with Normale audio which is further connected with Export Episode»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Export Episode which is finally connected with Podcast workflow complete»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Podcast workflow complete. Export Episode»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Export Episode is connected with Publish episode»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Publish episode which is then connected with Podcast workflow complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 0.6666666666666666 / 0; B3: 0.8571428571428571 / 0.

## test_branch_01

Источники: `runs/test_v1/test_branch_01/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Order Begins is connected with Check stock which is then connected with Item available? If Item available? is No then Reserve item and if Item available? is Yes then Request replenishment and if Item available? is Yes then Item available? Also, Reserve item is connected with both Order review complete and Order review complete which is then connected with both Order review complete and Order review complete. If Reservation dey is No then Reserve item and if Reservation dey is Yes then Request replenishment and if Reservation dey is No then Order review complete.

Кандидатные утверждения: {'supported_by_B0': 2, 'uncertain': 14}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Начало описано верно, но текст меняет местами No/Yes для Reserve item и Request replenishment относительно B0 и задания. Повторяющийся Order review complete и Reservation dey делают остальные фразы неоднозначными. Ошибочные условия не сформулированы как предложения исправления.

- «Order Begins is connected with Check stock»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Check stock which is then connected with Item available?»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Item available? If Item available?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Item available? is No then Reserve item»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Reserve item and if Item available?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Item available? is Yes then Request replenishment»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Request replenishment and if Item available?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Item available? is Yes then Item available?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Item available? Also, Reserve item»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Reserve item is connected with both Order review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Order review complete and Order review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Order review complete which is then connected with both Order review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Order review complete and Order review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Order review complete. If Reservation dey is No then Reserve item»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Reserve item and if Reservation dey is Yes then Request replenishment»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Request replenishment and if Reservation dey is No then Order review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_branch_02

Источники: `runs/test_v1/test_branch_02/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Expense review begins with Read expense claim being connected with Receipt claim which if Receipt claim is No then Reject reimbursement which if Receipt claim is Yes then Approve reimbursement which if Receipt claim is Yes then Record decision which if Record decision is Expense review complete then Expense review complete. Also, Receive reimbursement is connected with Record decision which if Record decision is Expense review complete then Expense review complete.

Кандидатные утверждения: {'supported_by_B0': 1, 'uncertain': 10}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Ответ содержит Receipt claim и Receive reimbursement вместо полных названий B0. При предположении, что Receipt claim означает Receipt attached?, направления Yes/No выглядят согласованными, но автоматическая замена имён не обоснована. Условия с Record decision/Expense review complete неясны. Подтверждённого конкретного замечания об ошибке нет.

- «Expense review begins with Read expense claim»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Read expense claim being connected with Receipt claim which if Receipt claim is No then Reject reimbursement»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Reject reimbursement which if Receipt claim is Yes then Approve reimbursement»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Approve reimbursement which if Receipt claim is Yes then Record decision»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Record decision which if Record decision»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Record decision is Expense review complete»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Expense review complete then Expense review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Expense review complete. Also, Receive reimbursement is connected with Record decision»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Record decision which if Record decision»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Record decision is Expense review complete»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Expense review complete then Expense review complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_branch_03

Источники: `runs/test_v1/test_branch_03/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Account recovery begins with Check security answer and If Check security answer is No then Answer correct? Also, If Answer correct? is Yes then Send reset link and If Answer correct? is No then Escalate to support. Also, If Answer correct? is Yes then Send reset link and If Answer correct? is No then Log recovery attempt. Also, If Log recovery attempt is Recovery attempt complete then Recovery attempt complete. If Recovery attempt complete is Yes then Send reset link and If Recovery attempt complete is No then Escalate to support. If Recovery attempt complete is Answer correct? then Recovery attempt and if Recovery attempt complete is No then Escalate to support.

Кандидатные утверждения: {'supported_by_B0': 1, 'uncertain': 21}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Часть условного пересказа верна: Answer correct? Yes → Send reset link и No → Escalate to support. Позже No → Log recovery attempt противоречит B0/заданию. Ветвления из Recovery attempt complete также не поддержаны графом. Рекомендации исправить реальную ошибку нет.

- «Account recovery begins with Check security answer»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Check security answer and If Check security answer»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Check security answer is No then Answer correct?»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Answer correct? Also, If Answer correct?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Answer correct? is Yes then Send reset link»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Send reset link and If Answer correct?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Answer correct? is No then Escalate to support»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Escalate to support. Also, If Answer correct?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Answer correct? is Yes then Send reset link»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Send reset link and If Answer correct?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Answer correct? is No then Log recovery attempt»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Log recovery attempt. Also, If Log recovery attempt»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Log recovery attempt is Recovery attempt complete»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Recovery attempt complete then Recovery attempt complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Recovery attempt complete. If Recovery attempt complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Recovery attempt complete is Yes then Send reset link»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Send reset link and If Recovery attempt complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Recovery attempt complete is No then Escalate to support»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Escalate to support. If Recovery attempt complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Recovery attempt complete is Answer correct?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Answer correct? then Recovery attempt and if Recovery attempt complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Recovery attempt complete is No then Escalate to support»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_branch_04

Источники: `runs/test_v1/test_branch_04/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Waste sorting begins with Inspect container which is then connected with Use recycling bin which is then connected with Use general waste bin. If Use recycling bin is no then Use general waste bin and if Use recycling bin is yes then Container recyclable? If Container recyclable is no then Clean sorting area and if Container recyclable is complete then Waste sorting complete. Also, Clean sorting area is connected with Waste sorting complete.

Кандидатные утверждения: {'supported_by_B0': 2, 'contradicted_by_B0': 2, 'uncertain': 7}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Текст утверждает Inspect container → Use recycling bin и Use recycling bin → Use general waste bin: оба прямых ребра отсутствуют в B0 и задании. Clean sorting area → Waste sorting complete описано правильно. Условия остальных фраз неоднозначны; диагностики геометрии или предложения исправления нет.

- «Waste sorting begins with Inspect container»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Inspect container which is then connected with Use recycling bin»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Use recycling bin which is then connected with Use general waste bin»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Use general waste bin. If Use recycling bin»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Use recycling bin is no then Use general waste bin»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Use general waste bin and if Use recycling bin»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Use recycling bin is yes then Container recyclable?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Container recyclable? If Container recyclable is no then Clean sorting area»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Clean sorting area and if Container recyclable is complete then Waste sorting complete»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Waste sorting complete. Also, Clean sorting area»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Clean sorting area is connected with Waste sorting complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_branch_05

Источники: `runs/test_v1/test_branch_05/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Delivery planning begins with Read destination which is then connected with Desioution which is then connected with Assign bicycle courier. If Assign bicycle courier is No then Send route detailed and if Assign van courier is No then Assign van courier. Also, Send route detailed is connected with Delivery planning complete which if Delivery planning complete is Delivery planning complete then Assign bicycle courier and if Delivery planning complete is Delivery planning complete then Send route detailed. Also, Send route detailed is connected with Delivery planning complete which if Delivery planning complete is Delivery planning complete then Assign bicycle courier and if Delivery planning complete is Delivery planning complete then Assign van courier.

Кандидатные утверждения: {'supported_by_B0': 1, 'uncertain': 17}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Первый переход Delivery planning begins → Read destination верен. Desioution и Send route detailed не соответствуют точным именам; их трактовка требует догадок. Условия из конечного Delivery planning complete не поддержаны B0/заданием. Явной рекомендации нет.

- «Delivery planning begins with Read destination»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Read destination which is then connected with Desioution which is then connected with Assign bicycle courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign bicycle courier. If Assign bicycle courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign bicycle courier is No then Send route detailed and if Assign van courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign van courier is No then Assign van courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign van courier. Also, Send route detailed is connected with Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete which if Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete is Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete then Assign bicycle courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign bicycle courier and if Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete is Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete then Send route detailed. Also, Send route detailed is connected with Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete which if Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete is Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete then Assign bicycle courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Assign bicycle courier and if Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete is Delivery planning complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Delivery planning complete then Assign van courier»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 1.0 / 1; B3: 1.0 / 1.

## test_loop_01

Источники: `runs/test_v1/test_loop_01/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Software release begins with Prepare build which is then connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete. Fix implementation is connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete. Also, Fix implementation is connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete.

Кандидатные утверждения: {'supported_by_B0': 7, 'contradicted_by_B0': 3, 'uncertain': 2}. Пропущенные в B0 рёбра: [('fix implementation', 'run test suite', '')]; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Prepare build → All tests pass? и Fix implementation → All tests pass? не являются прямыми рёбрами B0 или задания. Реальный пропуск B0 — возврат Fix implementation → Run test suite — не назван отсутствующей связью. Пересказ не диагностирует этот дефект.

- «Software release begins with Prepare build»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Prepare build which is then connected with All tests pass?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «All tests pass? which is then connected with Publish release»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Publish release which is finally connected with Software release complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Software release complete. Fix implementation»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Fix implementation is connected with All tests pass?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «All tests pass? which is then connected with Publish release»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Publish release which is finally connected with Software release complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Software release complete. Also, Fix implementation»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Fix implementation is connected with All tests pass?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «All tests pass? which is then connected with Publish release»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Publish release which is finally connected with Software release complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 0.923076923076923 / 0; B2: 0.923076923076923 / 0; B3: 0.923076923076923 / 0.

## test_loop_02

Источники: `runs/test_v1/test_loop_02/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Application begin is connected with Collect documents which is then connected with Review application which is further connected with Submit application. If Request missing documents are present then Submit application and if Request missing documents are No then Application complete? If Application complete? is No then Request missing documents and if Application workflow complete then Application workflow complete. Also, Submit application is connected with both Application workflow complete and Request missing documents. Also, Request missing documents is connected with both Collection documents and Revise application. Also, Revise application is connected with both Application workflow complete and Application application complete?

Кандидатные утверждения: {'supported_by_B0': 1, 'contradicted_by_B0': 1, 'uncertain': 14}. Пропущенные в B0 рёбра: [('submit application', 'application workflow complete', '')]; лишние: [('application complete', 'application workflow complete', '')].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Collect documents → Review application описано верно, Review application → Submit application ошибочно как прямое ребро B0/задания. В тексте есть желательная Submit application → Application workflow complete в конструкции 'both', но она не отмечена как отсутствующая в B0. Поэтому нельзя засчитать успешное обнаружение реальной ошибки; названия также искажены.

- «Collect documents which is then connected with Review application»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Review application which is further connected with Submit application»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Submit application. If Request missing documents»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Request missing documents are present then Submit application»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Submit application and if Request missing documents»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Request missing documents are No then Application complete?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Application complete? If Application complete?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Application complete? is No then Request missing documents»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Request missing documents and if Application workflow complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Application workflow complete then Application workflow complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Application workflow complete. Also, Submit application»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Submit application is connected with both Application workflow complete»: **uncertain**; ребро в B0=False, требуется заданием=True; подпись ветви не оценена.
- «Application workflow complete and Request missing documents»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Request missing documents. Also, Request missing documents»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Request missing documents is connected with both Collection documents and Revise application. Also, Revise application is connected with both Application workflow complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Application workflow complete and Application application complete?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 0.8571428571428571 / 0; B2: 0.8750000000000001 / 0; B3: 0.8750000000000001 / 0.

## test_loop_03

Источники: `runs/test_v1/test_loop_03/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Bread making begins with Mix Ingredients which is then connected with Dough elastic? which if Dough elastic? is No then Knead dough which is then connected with Bake loaf which is further connected with Bread making complete. Also, Bread making complete is connected with Dough elastic? which if Dough elastic? is No then Knead dough which is then connected with Bake loaf which is further connected with Bread making complete.

Кандидатные утверждения: {'supported_by_B0': 3, 'contradicted_by_B0': 4, 'uncertain': 5}. Пропущенные в B0 рёбра: [('knead dough', 'inspect dough', ''), ('dough elastic', 'bake loaf', 'yes')]; лишние: [('knead dough', 'inspect dough', 'yes'), ('inspect dough', 'bake loaf', '')].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Mix Ingredients → Dough elastic?, Knead dough → Bake loaf и Bread making complete → Dough elastic? не являются прямыми рёбрами B0/задания. Реальные дефекты B0 (неверная подпись возврата Yes и переход к выпечке от Inspect dough вместо решения) явно не диагностированы. Ответ повторяет ошибочный пересказ.

- «Bread making begins with Mix Ingredients»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Mix Ingredients which is then connected with Dough elastic?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Dough elastic? which if Dough elastic?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Dough elastic? is No then Knead dough»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Knead dough which is then connected with Bake loaf»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Bake loaf which is further connected with Bread making complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Bread making complete. Also, Bread making complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Bread making complete is connected with Dough elastic?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Dough elastic? which if Dough elastic?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Dough elastic? is No then Knead dough»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Knead dough which is then connected with Bake loaf»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Bake loaf which is further connected with Bread making complete»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 0.7142857142857143 / 0; B2: 0.588235294117647 / 0; B3: 0.7142857142857143 / 0.

## test_loop_04

Источники: `runs/test_v1/test_loop_04/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Translation Beginner is connected with Draft Translation which is then connected with Review terminology which is further connected with Terminology Consist? Also, Review terminology is connected with Deliver translation which is then connected with Translator complete. Also, Translator complete is connected with Revise word choices which is then connected with Submit translation. Also, Submit translation is connected with Translator complete which is finally connected with Translator complete.

Кандидатные утверждения: {'supported_by_B0': 1, 'uncertain': 2, 'contradicted_by_B0': 1}. Пропущенные в B0 рёбра: [('deliver translation', 'translation complete', '')]; лишние: [('terminology consistent', 'translation complete', '')].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Draft Translation → Review terminology описано верно. Review terminology → Deliver translation отсутствует и в B0, и в задании. Translation Beginner/Translator complete/Submit translation не разрешены точным сопоставлением. Реальные лишнее ребро решения к завершению и недостающее Deliver translation → Translation complete явно не названы ошибками.

- «Draft Translation which is then connected with Review terminology»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Review terminology which is further connected with Terminology Consist? Also, Review terminology»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Review terminology is connected with Deliver translation»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Deliver translation which is then connected with Translator complete. Also, Translator complete is connected with Revise word choices»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 0.8571428571428571 / 0; B2: 0.7999999999999999 / 0; B3: 0.6666666666666666 / 0.

## test_loop_05

Источники: `runs/test_v1/test_loop_05/visual/feedback.json`, `B0/scene.json`, задание в `tasks_public.json`, эталон `data/references.json`.

Текст критика:  Maintenance Begins is connected with Isolate machine which is then connected with Measure vibration which if Measure vibration is Vibration Acceptable? then Restore machine service and if Measure vibration is No then Adjust alignment. Also, Maintenance complete is connected with Adjust alignment which if Maintenance complete is Yes then Restore machine service and if Maintenance complete is No then Vibration Acceptable? Also, Maintenance complete is connected with Vibration Acceptable? If Vibration Acceptable? is No then Restore machine service and if Vibration Acceptable? is Yes then Adjust alignment. Also, Maintenance complete is connected with Measure vibration which if Measure vibration is Vibration Acceptable? is Yes then Restore machine service and if Measure vibration is No then Adjust alignment.

Кандидатные утверждения: {'supported_by_B0': 2, 'uncertain': 21, 'contradicted_by_B0': 3}. Пропущенные в B0 рёбра: []; лишние: [].

Качественный разбор ассистентом после эксперимента (не независимая разметка): Maintenance Begins → Isolate machine → Measure vibration описано верно. Maintenance complete → Adjust alignment, → Vibration Acceptable? и → Measure vibration отсутствуют в B0/задании. Фраза Vibration Acceptable? No → Restore machine service и Yes → Adjust alignment переворачивает реальные подписи ветвей. Конкретного полезного замечания нет.

- «Maintenance Begins is connected with Isolate machine»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Isolate machine which is then connected with Measure vibration»: **supported_by_B0**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Measure vibration which if Measure vibration»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Measure vibration is Vibration Acceptable?»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Vibration Acceptable? then Restore machine service»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Restore machine service and if Measure vibration»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Measure vibration is No then Adjust alignment»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Adjust alignment. Also, Maintenance complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Maintenance complete is connected with Adjust alignment»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Adjust alignment which if Maintenance complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Maintenance complete is Yes then Restore machine service»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Restore machine service and if Maintenance complete»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Maintenance complete is No then Vibration Acceptable?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Vibration Acceptable? Also, Maintenance complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Maintenance complete is connected with Vibration Acceptable?»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Vibration Acceptable? If Vibration Acceptable?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Vibration Acceptable? is No then Restore machine service»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Restore machine service and if Vibration Acceptable?»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Vibration Acceptable? is Yes then Adjust alignment»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Adjust alignment. Also, Maintenance complete»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Maintenance complete is connected with Measure vibration»: **contradicted_by_B0**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Measure vibration which if Measure vibration»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Measure vibration is Vibration Acceptable?»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Vibration Acceptable? is Yes then Restore machine service»: **uncertain**; ребро в B0=True, требуется заданием=True; подпись ветви не оценена.
- «Restore machine service and if Measure vibration»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.
- «Measure vibration is No then Adjust alignment»: **uncertain**; ребро в B0=False, требуется заданием=False; подпись ветви не оценена.

Изменения редактора (Edge F1 / полное совпадение): B0: 1.0 / 1; B2: 0.8235294117647058 / 0; B3: 0.8235294117647058 / 0.

