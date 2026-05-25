import httpx
import json
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class YandexGPTService:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.model_uri = f"gpt://{self.folder_id}/yandexgpt-lite"

        print(f"YandexGPT initialized with folder_id: {self.folder_id}")
        print(f"API Key exists: {bool(self.api_key)}")

    async def evaluate_answer(self, question: str, user_answer: str, difficulty: str, topic: str) -> Dict[str, Any]:
        """Оценка ответа пользователя через YandexGPT"""

        print(f"=== YandexGPT Evaluation ===")
        print(f"Topic: {topic}, Difficulty: {difficulty}")
        print(f"Question: {question[:100]}...")
        print(f"Answer length: {len(user_answer)} chars")

        prompt = f"""
Ты — эксперт по системному анализу с 10-летним опытом. Оцени ответ кандидата на собеседовании.

Вопрос: {question}

Уровень: {difficulty} (junior/middle/senior)
Тема: {topic}

Ответ кандидата: {user_answer}

Оцени ответ по критериям (каждый от 1 до 10):
- structure (структура ответа, логика изложения)
- technical_accuracy (техническая точность терминов)
- practical_examples (наличие примеров из практики)
- star_method (использование STAR методологии)
- communication (ясность и уверенность)

Также укажи:
- strengths (3 сильные стороны ответа)
- improvements (3 момента для улучшения)
- missing_points (чего не хватает)
- overall_score (общий балл 0-100)
- improved_answer (улучшенная версия ответа)

Ответ дай строго в формате JSON:
{{
    "scores": {{
        "structure": число_1_10,
        "technical_accuracy": число_1_10,
        "practical_examples": число_1_10,
        "star_method": число_1_10,
        "communication": число_1_10
    }},
    "strengths": ["строка", "строка", "строка"],
    "improvements": ["строка", "строка", "строка"],
    "missing_points": ["строка", "строка"],
    "overall_score": число_0_100,
    "improved_answer": "текст_улучшенного_ответа"
}}
"""

        async with httpx.AsyncClient() as client:
            try:
                print("Sending request to YandexGPT...")
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Api-Key {self.api_key}",
                        "x-folder-id": self.folder_id,
                        "Content-Type": "application/json"
                    },
                    json={
                        "modelUri": self.model_uri,
                        "completionOptions": {
                            "stream": False,
                            "temperature": 0.3,
                            "maxTokens": 2000
                        },
                        "messages": [
                            {
                                "role": "system",
                                "text": "Ты — эксперт по системному анализу. Отвечай только в формате JSON."
                            },
                            {
                                "role": "user",
                                "text": prompt
                            }
                        ]
                    },
                    timeout=30.0
                )

                print(f"YandexGPT response status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    ai_text = result["result"]["alternatives"][0]["message"]["text"]
                    print(f"AI Response received, length: {len(ai_text)} chars")
                    # Извлекаем JSON из ответа
                    try:
                        analysis = json.loads(ai_text)
                        return analysis
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"Raw AI response: {ai_text[:500]}")
                        return self._local_evaluation(question, user_answer)
                else:
                    print(f"YandexGPT error: {response.status_code} - {response.text}")
                    return self._local_evaluation(question, user_answer)

            except httpx.TimeoutException:
                print("YandexGPT timeout")
                return self._local_evaluation(question, user_answer)
            except Exception as e:
                print(f"YandexGPT exception: {e}")
                return self._local_evaluation(question, user_answer)

    def _local_evaluation(self, question: str, answer: str) -> Dict:
        """Локальная оценка с реальной зависимостью от ответа"""

        word_count = len(answer.split())
        has_numbers = any(char.isdigit() for char in answer)
        has_example = any(
            word in answer.lower() for word in ['например', 'пример', 'project', 'опыте', 'был', 'работал', 'делал'])
        has_risks = any(word in answer.lower() for word in ['риск', 'проблем', 'сложност', 'трудност'])
        has_alternatives = any(word in answer.lower() for word in ['альтернатив', 'вариант', 'другой', 'иначе'])
        has_star = any(word in answer.lower() for word in ['ситуац', 'задач', 'действ', 'результат', 'контекст'])
        has_metrics = any(word in answer.lower() for word in
                          ['процент', 'секунд', 'минут', 'час', 'дней', 'увеличил', 'уменьшил', 'сократил'])

        # Баллы зависят от наличия ключевых элементов
        structure_score = min(10, word_count // 50)
        tech_score = 5
        if has_risks:
            tech_score += 2
        if has_alternatives:
            tech_score += 2
        tech_score = min(10, tech_score)

        practical_score = 4
        if has_example:
            practical_score += 3
        if has_numbers:
            practical_score += 2
        if has_metrics:
            practical_score += 1
        practical_score = min(10, practical_score)

        star_score = 4
        if has_star:
            star_score += 6
        star_score = min(10, star_score)

        comm_score = 5
        if word_count > 150:
            comm_score += 3
        elif word_count > 50:
            comm_score += 1
        comm_score = min(10, comm_score)

        overall_score = min(100,
                            (structure_score * 2) +
                            (tech_score * 2) +
                            (practical_score * 2) +
                            (star_score * 2) +
                            (comm_score * 2)
                            )

        # Формируем разные отзывы в зависимости от ответа
        strengths = []
        improvements = []
        missing_points = []

        if structure_score >= 7:
            strengths.append("Хорошая структура ответа")
        else:
            improvements.append("Улучшите структуру: начните с контекста, затем действия, результат")

        if tech_score >= 7:
            strengths.append("Хорошее понимание технических аспектов")
        else:
            improvements.append("Изучите больше технических деталей по теме")

        if practical_score >= 7:
            strengths.append("Отличные практические примеры")
        else:
            improvements.append("Приведите конкретный пример из вашего опыта")
            missing_points.append("Нет практического примера")

        if star_score >= 8:
            strengths.append("Отличное использование STAR метода")
        elif star_score >= 5:
            strengths.append("Есть элементы STAR метода")
        else:
            improvements.append("Используйте STAR метод для структурирования ответа")
            missing_points.append("STAR метод не использован")

        if has_numbers or has_metrics:
            strengths.append("Хорошо, что используете конкретные цифры и метрики")
        else:
            improvements.append("Добавьте конкретные числовые метрики для подтверждения результатов")
            missing_points.append("Нет количественных показателей успеха")

        if has_risks:
            strengths.append("Упомянули риски и проблемы")
        else:
            improvements.append("Опишите риски и как вы их минимизировали")
            missing_points.append("Не указаны риски")

        if has_alternatives:
            strengths.append("Рассмотрели альтернативные решения")
        else:
            improvements.append("Опишите альтернативные подходы и почему выбрали именно этот")
            missing_points.append("Не рассмотрены альтернативы")

        # Гарантируем, что списки не пустые
        if len(strengths) == 0:
            strengths = ["Есть понимание темы", "Ответ дан"]

        if len(improvements) < 3:
            improvements.append("Попрактикуйтесь в ответах на подобные вопросы")

        if len(missing_points) < 2:
            missing_points.append("Можно добавить больше деталей")

        # Генерация улучшенного ответа
        improved_answer = self._generate_improved_answer(answer, has_numbers, has_example, has_star, has_metrics,
                                                         has_risks, has_alternatives)

        return {
            "scores": {
                "structure": structure_score,
                "technical_accuracy": tech_score,
                "practical_examples": practical_score,
                "star_method": star_score,
                "communication": comm_score
            },
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "missing_points": missing_points[:3],
            "overall_score": overall_score,
            "improved_answer": improved_answer
        }

    def _generate_improved_answer(self, answer: str, has_numbers: bool, has_example: bool, has_star: bool,
                                  has_metrics: bool, has_risks: bool, has_alternatives: bool) -> str:
        """Генерация улучшенного ответа на основе анализа"""

        improvements = []

        if not has_example:
            improvements.append("• Приведите конкретный пример из вашего опыта (проект, задача, ваша роль)")

        if not has_star:
            improvements.append("• Используйте STAR метод: Ситуация → Задача → Действие → Результат")

        if not has_numbers and not has_metrics:
            improvements.append(
                "• Добавьте цифры и метрики (например, 'сократили время на 30%', 'обработали 1 млн запросов')")

        if not has_risks:
            improvements.append("• Опишите риски и сложности, с которыми столкнулись, и как их преодолели")

        if not has_alternatives:
            improvements.append("• Рассмотрите альтернативные подходы и объясните, почему выбрали именно этот")

        if len(answer.split()) < 50:
            improvements.append("• Раскройте ответ подробнее, добавьте больше деталей")

        if improvements:
            return f"""
{answer}

💡 Рекомендации по улучшению ответа:
{chr(10).join(improvements)}

📝 Пример хорошего ответа по STAR:
• Ситуация: В проекте X мы столкнулись с проблемой Y
• Задача: Мне нужно было решить Z в условиях ограничений
• Действие: Я предпринял следующие шаги: 1) ... 2) ... 3) ...
• Результат: Это привело к улучшению показателей на N%
"""
        else:
            return answer + "\n\n💡 Отличный ответ! Продолжайте в том же духе."