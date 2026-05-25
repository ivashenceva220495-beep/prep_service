# app/services/ai_service.py
import httpx
import json
from typing import Dict, List, Optional
import os


class AIService:
    def __init__(self):
        # Используем бесплатный API от Google Gemini (нужен API ключ)
        # Получить ключ можно здесь: https://makersuite.google.com/app/apikey
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

        # Если нет API ключа, используем эмуляцию
        self.use_mock = not self.api_key

    async def generate_question(self, position: str, question_number: int, total: int,
                                previous_answers: List[Dict] = None) -> str:
        """Генерация вопроса на основе позиции и предыдущих ответов"""

        if self.use_mock:
            return self._mock_question(position, question_number)

        prompt = f"""
        Ты технический рекрутер. Проводи собеседование на позицию {position}.

        Это {question_number}-й вопрос из {total}.

        {f'Учитывая предыдущие ответы кандидата: {json.dumps(previous_answers, ensure_ascii=False)}' if previous_answers else ''}

        Сгенерируй технический вопрос, который:
        1. Соответствует уровню позиции {position}
        2. Проверяет глубокое понимание темы
        3. Интересный и нестандартный

        Верни ТОЛЬКО текст вопроса на русском языке.
        """

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"AI API error: {e}")

        return self._mock_question(position, question_number)

    async def evaluate_answer(self, position: str, question: str, answer: str) -> Dict:
        """Оценка ответа кандидата с анализом"""

        if self.use_mock:
            return self._mock_evaluation(answer)

        prompt = f"""
        Ты эксперт по техническим собеседованиям. Оцени ответ кандидата.

        Позиция: {position}
        Вопрос: {question}
        Ответ кандидата: {answer}

        Оцени по шкале 0-100 по критериям:
        1. Правильность (насколько ответ технически верен)
        2. Полнота (насколько полно раскрыта тема)
        3. Структурированность (логичность и четкость изложения)

        Также выдели:
        - Сильные стороны (2-3 пункта)
        - Что нужно улучшить (2-3 пункта)
        - Общую рекомендацию

        Верни ТОЛЬКО JSON в формате:
        {{
            "correctness": число,
            "completeness": число,
            "structure": число,
            "strengths": ["строка", "строка"],
            "improvements": ["строка", "строка"],
            "recommendation": "строка"
        }}
        """

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    # Извлекаем JSON из ответа
                    json_str = text.replace("```json", "").replace("```", "").strip()
                    return json.loads(json_str)
        except Exception as e:
            print(f"AI API error: {e}")

        return self._mock_evaluation(answer)

    async def generate_final_feedback(self, position: str, answers: List[Dict]) -> Dict:
        """Генерация финальной обратной связи"""

        if self.use_mock:
            return self._mock_final_feedback(answers)

        prompt = f"""
        Подведи итог собеседования на позицию {position}.

        Ответы кандидата: {json.dumps(answers, ensure_ascii=False, indent=2)}

        Сформируй финальную обратную связь:
        1. Технический уровень (оценка 0-100)
        2. Soft skills (оценка 0-100)
        3. Сильные стороны (3-5 пунктов)
        4. Зоны роста (3-5 пунктов)
        5. Итоговая рекомендация

        Верни ТОЛЬКО JSON в формате:
        {{
            "technical_score": число,
            "soft_skills_score": число,
            "strengths": ["строка", "строка"],
            "improvements": ["строка", "строка"],
            "recommendation": "строка",
            "level": "Junior/Middle/Senior"
        }}
        """

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_str = text.replace("```json", "").replace("```", "").strip()
                    return json.loads(json_str)
        except Exception as e:
            print(f"AI API error: {e}")

        return self._mock_final_feedback(answers)

    # MOCK функции для тестирования (когда нет API ключа)
    def _mock_question(self, position: str, question_number: int) -> str:
        questions_db = {
            "Python": [
                "Что такое GIL в Python и как он влияет на многопоточность?",
                "Чем отличается list от tuple? Приведите примеры использования.",
                "Объясните принцип работы декораторов. Напишите пример.",
                "Что такое list comprehension и как он работает?",
                "Как работают менеджеры контекста? Приведите пример with open()",
                "В чем разница между deepcopy и shallow copy?",
                "Что такое метаклассы в Python и зачем они нужны?",
                "Объясните принцип работы asyncio и event loop",
                "Что такое генераторы и в чем их преимущество?",
                "Как работает сборщик мусора в Python?"
            ],
            "JavaScript": [
                "В чем разница между var, let и const?",
                "Объясните принцип работы замыканий в JavaScript",
                "Что такое event loop и как он работает?",
                "В чем разница между == и ===?",
                "Что такое Promise и как он работает?",
                "Объясните принцип работы async/await",
                "Что такое spread operator и rest operator?",
                "Как работает прототипное наследование?",
                "Что такое debounce и throttle?",
                "Объясните принцип работы this в JavaScript"
            ]
        }

        # Определяем категорию
        category = "Python"
        if "javascript" in position.lower() or "js" in position.lower():
            category = "JavaScript"

        questions = questions_db.get(category, questions_db["Python"])
        return questions[(question_number - 1) % len(questions)]

    def _mock_evaluation(self, answer: str) -> Dict:
        """Эмуляция оценки на основе ключевых слов в ответе"""
        answer_lower = answer.lower()

        # Ключевые слова для оценки
        keywords = {
            "gil": ["gil", "global interpreter lock", "глобальная блокировка"],
            "list_vs_tuple": ["list", "tuple", "список", "кортеж", "изменяемый", "неизменяемый"],
            "decorator": ["декоратор", "decorator", "@", "wrapper", "обертка"],
            "async": ["async", "await", "асинхронный", "event loop", "asyncio"],
            "generator": ["генератор", "generator", "yield", "итератор"]
        }

        # Подсчет совпадений
        score = 50  # базовая оценка
        matched_keywords = 0

        for category, words in keywords.items():
            for word in words:
                if word in answer_lower:
                    matched_keywords += 1

        # Оценка на основе количества ключевых слов
        if matched_keywords >= 5:
            score = 85
        elif matched_keywords >= 3:
            score = 70
        elif matched_keywords >= 1:
            score = 55

        # Длина ответа тоже влияет на оценку
        if len(answer) > 500:
            score = min(score + 10, 95)
        elif len(answer) < 50:
            score = max(score - 15, 20)

        # Формируем обратную связь
        if score >= 80:
            strengths = ["Отличное понимание темы", "Хорошая структура ответа", "Приведены примеры"]
            improvements = ["Можно добавить больше деталей", "Упомянуть edge cases"]
            recommendation = "Отличный ответ! Продолжайте в том же духе."
        elif score >= 60:
            strengths = ["Базовое понимание темы", "Правильное направление мысли"]
            improvements = ["Углубить знания", "Добавить практические примеры", "Структурировать ответ"]
            recommendation = "Хороший ответ, но есть куда расти. Рекомендую изучить тему глубже."
        else:
            strengths = ["Есть понимание основ", "Попытка ответить"]
            improvements = ["Изучить тему более детально", "Практиковаться на задачах", "Читать документацию"]
            recommendation = "Ответ требует доработки. Рекомендую повторить материал и потренироваться."

        return {
            "correctness": score,
            "completeness": score - 5,
            "structure": score - 10,
            "strengths": strengths,
            "improvements": improvements,
            "recommendation": recommendation
        }

    def _mock_final_feedback(self, answers: List[Dict]) -> Dict:
        """Эмуляция финальной обратной связи"""
        scores = [a.get("score", 50) for a in answers]
        avg_score = sum(scores) / len(scores) if scores else 50

        if avg_score >= 80:
            level = "Middle+"
            recommendation = "Кандидат отлично подготовлен. Рекомендуется к найму на позицию Middle/Senior."
        elif avg_score >= 60:
            level = "Junior+"
            recommendation = "Кандидат хорошо подготовлен, но есть области для роста. Рекомендуется к рассмотрению."
        else:
            level = "Intern/Junior"
            recommendation = "Кандидату рекомендуется серьезно подготовиться перед следующим собеседованием."

        return {
            "technical_score": int(avg_score),
            "soft_skills_score": int(avg_score - 5),
            "strengths": ["Базовые знания технологии", "Понимание основных концепций"],
            "improvements": ["Углубить знания", "Больше практики", "Изучить best practices"],
            "recommendation": recommendation,
            "level": level
        }


# Создаем глобальный экземпляр сервиса
ai_service = AIService()