# Emotional Silero TTS Module

Микромодуль для генерации русской речи с заданными эмоциональными окрасками. Основан на Silero TTS с потоковой постобработкой через librosa.

## Установка и запуск
1. Клонируйте репозиторий.
2. Установите зависимости: `pip install -r requirements.txt`
3. Запустите тестовый файл: `python tts_core.py`

## Интеграция
Все параметры эмоций (скорость, тон, громкость) настраиваются в файле `config.json`. Приложение само скачает нужные веса нейросети при первой инициализации класса.

```python
from tts_core import EmotionalTTS

tts = EmotionalTTS()
tts.generate(
    text="Оставьте меня в покое!", 
    emotion="anger", 
    output_path="result.wav"
)