# OCR Desktop (Simplified)

Упрощенное локальное desktop-приложение для распознавания текста с изображения.

## Что умеет
- Drag-and-drop изображения в окно
- Поворот изображения перед OCR (влево/вправо)
- Выделение области (crop) для распознавания только нужного фрагмента
- Масштабирование предпросмотра (`+`, `-`, колесо мыши) и перемещение по изображению (drag мышью)
- OCR через `pytesseract` (языки `rus+eng`)
- Редактирование распознанного текста вручную
- Сохранение текущего текста в историю по кнопке
- История с колонками: дата, время (чч:мм), текст
- Открытие полной предыдущей записи в текстовом поле по клику на строку истории

## Стек
- PySide6
- OpenCV
- pytesseract
- SQLite

## Запуск через UV

1. Создать окружение:

```bash
uv venv
```

2. Активировать окружение и установить зависимости:

```bash
uv pip install -r requirements.txt
```

3. Установить Tesseract OCR (Windows):
- Обычно: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Добавить языковые пакеты `rus` и `eng`

Если путь другой, задать переменную окружения:

PowerShell:

```powershell
$env:TESSERACT_CMD = "D:\tools\tesseract\tesseract.exe"
```

CMD:

```cmd
set TESSERACT_CMD=D:\tools\tesseract\tesseract.exe
```

4. Запустить приложение:

```bash
python main.py
```
