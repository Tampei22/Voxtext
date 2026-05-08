"""Reference phrases used for WER/CER benchmarking — 20 per supported language."""

TEST_PHRASES: dict[str, list[str]] = {
    "ro": [
        # Simple — everyday speech
        "Bună ziua, cum vă numiți?",
        "Astăzi este o zi frumoasă afară.",
        "Vă rog să repetați mai rar.",
        "Am comandat două cafele și o prăjitură.",
        "Temperatura de afară este de douăzeci de grade.",
        "Mâine mergem la munte cu întreaga familie.",
        "Cartea aceasta este foarte interesantă.",
        "Deschideți fereastra, vă rog frumos.",
        "Vreau să cumpăr un bilet de tren pentru mâine.",
        "Îmi place foarte mult muzica clasică.",
        # Medium — longer or more complex
        "Sistemul de recunoaștere vocală funcționează bine.",
        "Recunoașterea automată a vorbirii este utilă.",
        "Calculatorul meu nu funcționează corect astăzi.",
        "Vă rog să traduceți această propoziție în română.",
        "Am terminat de citit cartea săptămâna trecută.",
        # Technical / domain-specific
        "Programul de calculator analizează datele audio în timp real.",
        "Recunoașterea vorbirii necesită algoritmi de învățare automată.",
        "Modelul neuronal procesează semnalul acustic în milisecunde.",
        "Rata de eroare la nivel de cuvânt măsoară acuratețea transcrierii.",
        "Vă mulțumesc frumos pentru ajutorul dumneavoastră prețios.",
    ],
    "ru": [
        # Simple — everyday speech
        "Добрый день, как вас зовут?",
        "Сегодня на улице хорошая погода.",
        "Пожалуйста, говорите немного медленнее.",
        "Я заказал два кофе и пирожное.",
        "На улице сегодня двадцать градусов тепла.",
        "Завтра мы едем в горы всей семьёй.",
        "Эта книга очень интересная и познавательная.",
        "Откройте окно, пожалуйста.",
        "Я хочу купить билет на поезд на завтра.",
        "Мне очень нравится классическая музыка.",
        # Medium — longer or more complex
        "Система распознавания речи работает хорошо.",
        "Автоматическое распознавание речи очень полезно.",
        "Мой компьютер сегодня работает неправильно.",
        "Пожалуйста, переведите это предложение на русский.",
        "Я закончил читать книгу на прошлой неделе.",
        # Technical / domain-specific
        "Компьютерная программа анализирует аудиоданные в реальном времени.",
        "Распознавание речи требует алгоритмов машинного обучения.",
        "Нейронная модель обрабатывает акустический сигнал за миллисекунды.",
        "Частота ошибок на уровне слов измеряет точность транскрипции.",
        "Благодарю вас за вашу ценную помощь и поддержку.",
    ],
    "en": [
        # Simple — everyday speech
        "Good morning, what is your name?",
        "Today the weather outside is beautiful.",
        "Please speak a little more slowly.",
        "I ordered two coffees and a pastry.",
        "The temperature outside is twenty degrees today.",
        "Tomorrow we are going to the mountains with the whole family.",
        "This book is very interesting and educational.",
        "Please open the window.",
        "I want to buy a train ticket for tomorrow.",
        "I really enjoy classical music very much.",
        # Medium — longer or more complex
        "The speech recognition system works very well.",
        "Automatic speech recognition is very useful.",
        "My computer is not working correctly today.",
        "Please translate this sentence into English for me.",
        "I finished reading the book last week.",
        # Technical / domain-specific
        "The computer program analyzes audio data in real time.",
        "Speech recognition requires machine learning algorithms.",
        "The neural model processes the acoustic signal in milliseconds.",
        "Word error rate measures the accuracy of the transcription.",
        "Thank you very much for your valuable help and support.",
    ],
}
