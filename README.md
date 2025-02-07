# Фильтр желтушных новостей

Пока поддерживается только один новостной сайт - [ИНОСМИ.РУ](https://inosmi.ru/). Для него разработан специальный адаптер, умеющий выделять текст статьи на фоне остальной HTML разметки. Для других новостных сайтов потребуются новые адаптеры, все они будут находиться в каталоге `adapters`. Туда же помещен код для сайта ИНОСМИ.РУ: `adapters/inosmi_ru.py`.

# Как установить

Вам понадобится Python версии 3.7 или старше. Для установки пакетов рекомендуется создать виртуальное окружение.

Первым шагом установите пакеты:

```python3
pip install -r requirements.txt
```

# Как запустить

```python3
python server.py
```

Пример запроса:
```  
http://127.0.0.1:8081/?urls=https://inosmi.ru/20221222/zemlya-259086442.html,https://inosmi.ru/20221222/yandeks-259084346.html,https://anyio.readthedocs.io/en/latest/tasks.html,https://inosmi.ru/20221221/oligarkhi-259041447.ht
```

# Как запустить тесты

Для тестирования используется [pytest](https://docs.pytest.org/en/latest/), тестами покрыты фрагменты кода сложные в отладке: text_tools.py и адаптеры. Команды для запуска тестов:

```
python -m pytest main.py
```

```
python -m pytest adapters/inosmi_ru.py
```

```
python -m pytest text_tools.py
```
