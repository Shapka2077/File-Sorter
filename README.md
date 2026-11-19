# File Sorter

Настольная программа для ручной сортировки видео по дате в начале имени файла.
Рекомендуется сначала проверить работу на копиях небольшого набора файлов.

Готовая программа: `dist\FileSorter.exe`. Папки с датами создаются в выбранной
папке назначения. При совпадении имён программа спрашивает, что делать.

Для запуска нужен Python 3 с поддержкой Tkinter:

```powershell
python app.py
```

Запуск тестов:

```powershell
python -m unittest discover -s tests -v
```

Для повторной сборки с установленным в `.venv` PyInstaller:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name FileSorter app.py
```

Дополнительные форматы сохраняются в `%APPDATA%\File Sorter\settings.json`.
На файловых системах без поддержки жёстких ссылок безопасное копирование без
перезаписи может завершиться ошибкой. Программа сообщит об этом в отчёте.
