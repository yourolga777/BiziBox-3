# Установка

## Системные требования

- Windows 10/11 (64-бит)
- 2 ГБ ОЗУ, ~1 ГБ свободного места

## Portable-версия (рекомендуется)

1. Скачайте `BiziBox.exe` со [страницы релизов](https://github.com/yourolga777/BiziBox-2/releases/latest).
2. Поместите файл в любую папку (например, `D:\BiziBox`).
3. Запустите `BiziBox.exe` — окно консоли не появляется, приложение запускается в фоне и само открывает браузер.
4. В системном трее появится иконка **BiziBox**: «Открыть BiziBox» / «Выход».

Все данные создаются рядом с exe: в папке `data\users\<ваш_логин>\` хранятся база, настройки каналов и вложения.

## Запуск из исходного кода

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 7910

# Frontend (второй терминал)
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:5173`.

## Обновление

Для portable-версии: скачайте новую версию `BiziBox.exe` и замените старый файл. Ваши данные сохранятся — они лежат в папке `data\` рядом с exe, а не внутри самого файла.
