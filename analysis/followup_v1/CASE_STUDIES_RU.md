# Три разбора сохранённых случаев

Случаи выбраны после просмотра результатов для иллюстрации, не как репрезентативная выборка. Отдельная история изменения не доказывает его причину. Рёбра сопоставлены по нормализованным названиям, направлению и подписи.

## Частичное улучшение: test_loop_02, B0 → B3

Edge F1: 0.8571 → 0.8750; полное совпадение: 0 → 0; геометрические ошибки: 1 → 1.

Программные замечания B0: [{'code': 'edge_label_overlap', 'severity': 'warning', 'affected_ids': ['e6', 'Application complete?'], 'message': 'Label of edge e6 overlaps node Application complete? description.'}, {'code': 'edge_through_node', 'severity': 'error', 'affected_ids': ['e7', 'Submit application'], 'message': 'Edge e7 crosses unrelated node Submit application.'}]

Визуальный текст:  Application begin is connected with Collect documents which is then connected with Review application which is further connected with Submit application. If Request missing documents are present then Submit application and if Request missing documents are No then Application complete? If Application complete? is No then Request missing documents and if Application workflow complete then Application workflow complete. Also, Submit application is connected with both Application workflow complete and Request missing documents. Also, Request missing documents is connected with both Collection documents and Revise application. Also, Revise application is connected with both Application workflow complete and Application application complete?

Добавленные рёбра: [('submit application', 'application workflow complete', ''), ('submit application', 'request missing documents', '')]. Удалённые: [].

Проверяемые артефакты: `runs/test_v1/test_loop_02/B0/scene.json`, `B3/scene.json`, `visual/feedback.json`, `B3/call_repair_0.json`. PNG находятся рядом с JSON.

## Без изменения измеренного качества: test_loop_01, B0 → B3

Edge F1: 0.9231 → 0.9231; полное совпадение: 0 → 0; геометрические ошибки: 0 → 0.

Программные замечания B0: [{'code': 'edge_label_overlap', 'severity': 'warning', 'affected_ids': ['e4', 'All tests pass?'], 'message': 'Label of edge e4 overlaps node All tests pass? description.'}]

Визуальный текст:  Software release begins with Prepare build which is then connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete. Fix implementation is connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete. Also, Fix implementation is connected with All tests pass? which is then connected with Publish release which is finally connected with Software release complete.

Добавленные рёбра: []. Удалённые: [].

Проверяемые артефакты: `runs/test_v1/test_loop_01/B0/scene.json`, `B3/scene.json`, `visual/feedback.json`, `B3/call_repair_0.json`. PNG находятся рядом с JSON.

## Регрессия правильной схемы: test_chain_01, B0 → B3

Edge F1: 1.0000 → 0.8571; полное совпадение: 1 → 0; геометрические ошибки: 0 → 3.

Программные замечания B0: []

Визуальный текст:  Parcel workflow begins with Receiver parcel connected with Wrought parcel which is then connected with Attach shipping label which is further connected with Dispatch parcel. Attach shipping label is connected with both Parcel workflow complete and Print shipping label which is then connected with both Parcel workflow and Dispatch parcel.

Добавленные рёбра: [('attach shipping label', 'parcel workflow complete', 'no'), ('print shipping label', 'parcel workflow complete', 'yes')]. Удалённые: [].

Проверяемые артефакты: `runs/test_v1/test_chain_01/B0/scene.json`, `B3/scene.json`, `visual/feedback.json`, `B3/call_repair_0.json`. PNG находятся рядом с JSON.

