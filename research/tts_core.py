import os
import json
import torch
import librosa
import soundfile as sf
import numpy as np


class EmotionalTTS:
    def __init__(self, config_path="config.json"):
        # Читаем конфигурацию
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        # Для простого продакшена берем CPU, он отлично тянет Силеро
        self.device = torch.device("cpu")
        self.sample_rate = self.config["sample_rate"]
        self.speaker = self.config["speaker"]

        print("Загрузка базовой модели Silero в память...")
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v4_ru",
            trust_repo=True  # Добавляем этот параметр, чтобы убрать Warning
        )
        self.model.to(self.device)
        print("Движок инициализирован.")

    def generate(self, text, emotion="neutral", output_path="output.wav"):
        # Ищем настройки эмоции, иначе берем нейтральную
        emo_settings = self.config["emotions"].get(emotion, self.config["emotions"]["neutral"])

        # Шаг 1: Генерируем "плоский" базовый звук
        audio_tensor = self.model.apply_tts(
            text=text,
            speaker=self.speaker,
            sample_rate=self.sample_rate
        )

        # Перегоняем тензор в numpy массив для аудио-эффектов
        audio_np = audio_tensor.numpy()

        # Шаг 2: Накладываем эмоциональные фильтры
        if emo_settings["speed"] != 1.0:
            audio_np = librosa.effects.time_stretch(y=audio_np, rate=emo_settings["speed"])

        if emo_settings["pitch_steps"] != 0:
            audio_np = librosa.effects.pitch_shift(
                y=audio_np,
                sr=self.sample_rate,
                n_steps=emo_settings["pitch_steps"]
            )

        audio_np = np.clip(audio_np * emo_settings["volume"], -1.0, 1.0)

        # Шаг 3: Сохраняем финальный результат
        sf.write(output_path, audio_np, self.sample_rate)
        return output_path


# Тестовый блок для локальной проверки
if __name__ == "__main__":
    engine = EmotionalTTS()
    engine.generate("Здравствуйте, ваш расчетный счет успешно открыт", emotion="anger", output_path="test_anger.wav")
    print("Проверка пройдена. Файл test_anger.wav сохранен.")