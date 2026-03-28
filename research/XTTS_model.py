import torch
from TTS.api import TTS
import os
import zipfile

class OzonManagerTTS:
    def __init__(self, dataset_path):
        print("🚀 Инициализация XTTS v2... Готовим конвейер.")
        os.system('export PATH="$(brew --prefix)/bin:$PATH"')
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
        self.dataset_path = dataset_path
        self.output_dir = "ozon_final_audio"
        self.zip_name = "ozon_voice_results.zip"
        
        self.emotion_map = {
            "neutral": "sample_0_neutral.wav",
            "questioning": "sample_1_questioning.wav",
            "anger": "sample_3_anger.wav",
            "admiration": "sample_4_admiration.wav",
            "surprise": "sample_5_surprise.wav",
            "sarcasm": "sample_6_sarcasm.wav",
            "sadness": "sample_7_sadness.wav",
            "fear": "sample_8_fear.wav",
            "disgust": "sample_9_disgust.wav"
        }
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def process_dataset(self, data):
        lines = data.strip().split('\n')
        generated_files = []
        
        for index, line in enumerate(lines):
            if '|' in line:
                text, emo_tag = [item.strip() for item in line.split('|')]
                ref_file = self.emotion_map.get(emo_tag, "sample_0_neutral.wav")
                full_ref_path = os.path.join(self.dataset_path, ref_file)
                
                if not os.path.exists(full_ref_path):
                    full_ref_path = os.path.join(self.dataset_path, "sample_0_neutral.wav")

                filename = f"{index+1:02d}_{emo_tag}.wav"
                output_path = os.path.join(self.output_dir, filename)
                
                print(f"🎙 [{emo_tag.upper()}] -> {filename}")
                self.tts.tts_to_file(text=text, speaker_wav=full_ref_path, language="ru", file_path=output_path)
                generated_files.append(output_path)
        
        self.make_zip(generated_files)

    def make_zip(self, files):
        print(f"📦 Упаковка {len(files)} файлов в архив {self.zip_name}...")
        with zipfile.ZipFile(self.zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                # Кладем файл в архив без лишних папок внутри
                zipf.write(file, os.path.basename(file))
        
        size = os.path.getsize(self.zip_name) / (1024 * 1024)
        print(f"✅ Успех! Архив готов: {self.zip_name} ({size:.2f} MB)")

if __name__ == "__main__":
    dataset_folder = "/Users/sepren/Downloads/ozon_tts_audio_dataset"
    raw_data = """
Здравствуйте! Поздравляю вас с регистрацией на Ozon. Я ваш менеджер и готов помочь.|neutral
Я только что зарегистрировался и пока не подключил свой расчетный счет.|neutral
Подождите, какой счет вы имеете в виду? Я новичок в этом деле.|questioning
Оставьте меня в покое! Вы уже третий раз сегодня звоните!|anger
Хватит! Я не могу больше переносить вашу манипуляцию и предложения.|anger
Могли бы вы мне рассказать подробнее о возможностях оптимизации операций?|questioning
У меня уже есть счет в другом банке, обслуживание стоит около пятисот рублей.|neutral
Очень полезно. Буду изучать возможности автоматизации поставок.|admiration
Вау, этот интерфейс просто невероятен, как же удобно все сделано!|admiration
Неужели можно так просто подключить счет? Потрясающе!|surprise
Да конечно, прям уж бесплатно вы все делаете, так я и поверил.|sarcasm
Как же жаль, что у меня не получилось настроить магазин с первого раза...|sadness
Ой, я случайно удалил все товары, что же теперь делать?|fear
Фу, ну и запутанная же у вас система отчетов, просто ужас какой-то.|disgust
Благодарю вас за доверие! Ваш успех это наша цель.|admiration
    """
    generator = OzonManagerTTS(dataset_folder)
    generator.process_dataset(raw_data)