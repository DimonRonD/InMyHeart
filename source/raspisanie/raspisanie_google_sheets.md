# Расписание INMYHEART — инструкция Google Sheets

## Назначение
Оперативное редактирование режима работы администратором без деплоя кода RAG.

## Ссылка на мастер-таблицу
https://docs.google.com/spreadsheets/d/example-inmyheart-schedule/edit

## Листы в таблице
1. **Режим клиники** — экспорт в `raspisanie_rabota_kliniki.csv`
2. **Врачи** — экспорт в `raspisanie_vrachey.csv`
3. **Лаборатория и диагностика** — экспорт в `raspisanie_laboratoriya_diagnostika.csv`

## Порядок обновления базы знаний
1. Внести изменения в Google Sheets.
2. Скачать каждый лист как CSV (разделитель «;»).
3. Заменить файлы в папке `source/raspisanie/`.
4. Переиндексировать векторную базу Chroma.

## Ответственный
Администратор смены — email info@inmyheart-clinic.ru, внутренний чат «Расписание».
