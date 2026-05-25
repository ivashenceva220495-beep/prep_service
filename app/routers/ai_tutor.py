from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.interview import InterviewSession, AnswerHistory
from app.schemas.schemas import QuestionRequest, AnswerRequest, AnalysisResponse, SessionResponse
from app.services.yandex_gpt import YandexGPTService
from typing import List, Dict
from datetime import datetime
import random
import json

router = APIRouter(prefix="/api/ai-tutor", tags=["ai-tutor"])

yandex_gpt = YandexGPTService()

# ПОЛНАЯ БАЗА ВОПРОСОВ ПО УРОВНЯМ И ТЕМАМ
QUESTIONS = {
    "requirements": {
        "junior": [
            "Что такое функциональные и нефункциональные требования? Приведите по 3 примера.",
            "Как вы собираете требования от стейкхолдеров? Опишите процесс.",
            "Что такое user story и как ее правильно оформить? Напишите шаблон.",
            "Кто такие стейкхолдеры и как выявлять их потребности?",
            "Что такое acceptance criteria? Приведите пример.",
            "Чем отличается бизнес-требование от функционального?",
            "Что такое MVP и зачем он нужен?",
            "Какие методы приоритизации требований вы знаете?",
            "Что такое бэклог требований и как его поддерживать?",
            "Какие инструменты для управления требованиями вы знаете?"
        ],
        "middle": [
            "Как управлять конфликтами требований между разными стейкхолдерами?",
            "Что такое трассировка требований и зачем она нужна? Как ее реализовать?",
            "Как оценивать трудоёмкость реализации требований?",
            "Как работать с изменением требований в середине спринта?",
            "Что такое 'технический долг' в требованиях?",
            "Как проверять требования на полноту и непротиворечивость?",
            "Какие метрики качества требований вы используете?",
            "Как адаптировать требования под Waterfall и Agile?",
            "Что такое use case и чем он отличается от user story?",
            "Как проводить анализ влияния изменений требований?"
        ],
        "senior": [
            "Как выстроить процесс requirements engineering с нуля в компании?",
            "Как оценивать риски, связанные с требованиями, на ранних этапах?",
            "Как управлять требованиями в распределённой команде из 50+ человек?",
            "Какие методологии моделирования требований вы предпочитаете?",
            "Как интегрировать требования с системой тестирования?",
            "Как автоматизировать проверку качества требований?",
            "Как провести миграцию с устаревшей системы требований на новую?",
            "Как работать с требованиями при outsourcing/outstaffing проектах?",
            "Как выстраивать культуру работы с требованиями в команде?",
            "Как оценить ROI от внедрения процесса управления требованиями?"
        ]
    },
    "architecture": {
        "junior": [
            "Что такое архитектура программного обеспечения?",
            "Чем отличается монолит от микросервисов? Приведите плюсы и минусы.",
            "Что такое REST API? Назовите основные принципы.",
            "Что такое ACID в контексте баз данных? Объясните каждое свойство.",
            "Что такое трёхуровневая архитектура? Опишите уровни.",
            "Что такое API Gateway и зачем он нужен?",
            "Что такое балансировка нагрузки? Какие алгоритмы знаете?",
            "Что такое stateless и stateful приложения?",
            "Что такое вертикальное и горизонтальное масштабирование?",
            "Что такое CI/CD и как это связано с архитектурой?"
        ],
        "middle": [
            "Как выбрать между микросервисами и монолитом? Какие критерии?",
            "Как проектировать high availability систему?",
            "Какие типы кэширования и стратегии инвалидации вы знаете?",
            "Что такое eventual consistency и когда она допустима?",
            "Как спроектировать систему для геораспределённых пользователей?",
            "Какие паттерны отказоустойчивости вы знаете? Circuit Breaker, Retry...",
            "Что такое CQRS и когда его применять?",
            "Как проектировать API с учётом версионирования?",
            "Что такое saga pattern для распределённых транзакций?",
            "Как проводить нагрузочное тестирование архитектуры?"
        ],
        "senior": [
            "Как спроектировать систему на миллионы запросов в секунду?",
            "Сравните event-driven и request-response архитектуры",
            "Как решать проблему distributed transactions в микросервисах?",
            "Как проектировать систему с zero downtime deployment?",
            "Что такое mesh-сети и service mesh?",
            "Как проводить архитектурный review существующей системы?",
            "Как мигрировать с монолита на микросервисы без остановки?",
            "Как проектировать систему с учётом GDPR и требований безопасности?",
            "Что такое архитектурные кванты и DDD?",
            "Как оценивать технологический долг архитектуры?"
        ]
    },
    "databases": {
        "junior": [
            "В чем разница между SQL и NoSQL базами данных?",
            "Что такое индекс в БД и зачем он нужен?",
            "Объясните типы JOIN в SQL (INNER, LEFT, RIGHT, FULL)",
            "Что такое первичный ключ и внешний ключ?",
            "Что такое нормализация и денормализация?",
            "Что такое транзакция и её свойства ACID?",
            "Какие типы данных в SQL вы знаете?",
            "Что такое GROUP BY и агрегатные функции?",
            "Что такое подзапрос и когда его использовать?",
            "Что такое VIEW и зачем он нужен?"
        ],
        "middle": [
            "Как выбирать между PostgreSQL, MongoDB и Cassandra?",
            "Что такое шардирование и репликация?",
            "Как оптимизировать медленные запросы?",
            "Что такое explain plan и как его читать?",
            "Какие стратегии индексации существуют?",
            "Когда стоит использовать NoSQL вместо SQL?",
            "Что такое deadlock и как его избежать?",
            "Как проводить миграцию данных без даунтайма?",
            "Что такое connection pooling и как его настроить?",
            "Какие паттерны работы с БД в микросервисах?"
        ],
        "senior": [
            "Как проектировать схему БД для социальной сети с миллионами пользователей?",
            "Как обеспечивать consistency в распределённых БД?",
            "Стратегии миграции данных в крупных системах",
            "Как выбирать между согласованностью, доступностью и устойчивостью к разделению?",
            "Что такое базы данных нового поколения (NewSQL)?",
            "Как проектировать мультиарендную БД для SaaS?",
            "Как восстанавливаться после коррупции данных?",
            "Как реализовать аудит всех изменений в БД?",
            "Что такое HTAP-системы и когда они нужны?",
            "Как проектировать кэш-стратегии в связке с БД?"
        ]
    },
    "integration": {
        "junior": [
            "Что такое API и какие типы API вы знаете?",
            "Синхронная vs асинхронная коммуникация: сравнение",
            "Что такое message broker и зачем он нужен?",
            "REST vs SOAP: сравнение, плюсы и минусы",
            "Что такое Webhook и как он работает?",
            "Какие HTTP методы существуют и для чего они нужны?",
            "Что такое HTTP статусы? Назовите основные группы.",
            "Что такое OpenAPI/Swagger?",
            "Authentication vs Authorization: в чем разница?",
            "Что такое API rate limiting и зачем он нужен?"
        ],
        "middle": [
            "Kafka vs RabbitMQ: когда что выбрать? Сравнение",
            "Как обеспечивать idempotency в API интеграциях?",
            "Опишите паттерны retry и circuit breaker",
            "Как проектировать событийно-ориентированную архитектуру?",
            "Как обеспечивать exactly-once delivery в сообщениях?",
            "Что такое dead letter queue и как её обрабатывать?",
            "Как тестировать API интеграции?",
            "Как документация API влияет на качество интеграций?",
            "Как обрабатывать ошибки в асинхронных интеграциях?",
            "Что такое API Gateway composition pattern?"
        ],
        "senior": [
            "Как проектировать интеграцию legacy систем с современными?",
            "Как отлаживать проблемы в распределённой системе?",
            "Стратегии версионирования API",
            "Как построить платформу для управления всеми API компании?",
            "Что такое GraphQL federation?",
            "Как обеспечивать observability в системах интеграций?",
            "Как управлять секретами и сертификатами в интеграциях?",
            "Как проектировать B2B интеграции?",
            "Что такое change data capture (CDC) и когда применять?",
            "Как проводить нагрузочное тестирование интеграционных шин?"
        ]
    },
    "security": {
        "junior": [
            "Что такое OWASP Top 10? Назовите основные угрозы.",
            "Что такое SQL-инъекция и как защититься?",
            "Что такое XSS и как защититься?",
            "Что такое HTTPS и как он работает?",
            "Что такое JWT токены? Структура и применение.",
            "Хеширование vs шифрование: в чем разница?",
            "Что такое CORS и как его настроить?",
            "Что такое SSL/TLS сертификаты?",
            "Принцип наименьших привилегий",
            "Валидация ввода данных: зачем и как?"
        ],
        "middle": [
            "Методы аутентификации и авторизации: сравнение",
            "Как защитить API от DDoS атак?",
            "Как реализовать audit log для комплаенса?",
            "API keys vs OAuth 2.0 vs JWT: когда что использовать?",
            "Как обрабатывать секреты в микросервисной архитектуре?",
            "Что такое SAST и DAST?",
            "Как проектировать систему с учётом GDPR?",
            "Что такое Security by Design?",
            "Как проводить threat modeling?",
            "Инструменты для сканирования уязвимостей"
        ],
        "senior": [
            "Как построить Zero Trust архитектуру?",
            "Как внедрить Security в CI/CD pipeline?",
            "Как организовать SOC и реагирование на инциденты?",
            "Как проводить пентесты и баг-баунти?",
            "Как управлять уязвимостями в open-source зависимостях?",
            "Как обеспечивать безопасность при использовании AI в продукте?",
            "Что такое федеративная аутентификация (SSO, SAML, LDAP)?",
            "Как проектировать систему для медицинских данных (HIPAA)?",
            "Как защитить данные в облачных хранилищах?",
            "Как автоматизировать compliance проверки?"
        ]
    }
}


def get_user_id_from_session(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user.get("sub")


@router.post("/start-session", response_model=SessionResponse)
async def start_session(
        request: Request,
        question_req: QuestionRequest,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    topic_questions = QUESTIONS.get(question_req.topic, QUESTIONS["requirements"])
    difficulty_questions = topic_questions.get(question_req.difficulty, topic_questions["middle"])

    # Берем первый вопрос из списка
    question = difficulty_questions[0]

    session = InterviewSession(
        user_id=user_id,
        session_type="practice",
        topic=question_req.topic,
        difficulty=question_req.difficulty,
        questions_asked=[question],
        answers_given=[],
        scores=[],
        feedback=[]
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        session_id=session.id,
        question=question,
        topic=question_req.topic,
        difficulty=question_req.difficulty
    )


@router.get("/next-question/{session_id}")
async def get_next_question(
        session_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Получаем список вопросов для данной темы и сложности
    topic_questions = QUESTIONS.get(session.topic, QUESTIONS["requirements"])
    difficulty_questions = topic_questions.get(session.difficulty, topic_questions["middle"])

    # Определяем индекс следующего вопроса
    current_count = len(session.questions_asked or [])

    # Берем следующий вопрос по порядку
    if current_count >= len(difficulty_questions):
        # Если вопросы закончились, берем случайный
        next_question = random.choice(difficulty_questions)
    else:
        next_question = difficulty_questions[current_count]

    # Добавляем вопрос в сессию
    questions_asked = session.questions_asked or []
    questions_asked.append(next_question)
    session.questions_asked = questions_asked

    await db.commit()

    return {"question": next_question}


@router.post("/analyze-answer", response_model=AnalysisResponse)
async def analyze_answer(
        request: Request,
        answer_req: AnswerRequest,
        db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_session(request)

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == answer_req.session_id,
            InterviewSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Получаем последний вопрос из сессии
    question = session.questions_asked[-1] if session.questions_asked else ""

    # Анализируем ответ
    analysis = await yandex_gpt.evaluate_answer(
        question=question,
        user_answer=answer_req.answer,
        difficulty=session.difficulty,
        topic=session.topic
    )

    # Сохраняем историю
    history = AnswerHistory(
        user_id=user_id,
        question=question,
        answer=answer_req.answer,
        ai_feedback=json.dumps(analysis),
        score=analysis.get("overall_score", 0)
    )
    db.add(history)

    # Обновляем сессию
    answers_given = session.answers_given or []
    answers_given.append(answer_req.answer)
    session.answers_given = answers_given

    scores = session.scores or []
    scores.append(analysis.get("overall_score", 0))
    session.scores = scores

    feedback = session.feedback or []
    feedback.append(analysis)
    session.feedback = feedback

    await db.commit()

    return AnalysisResponse(
        scores=analysis.get("scores", {}),
        strengths=analysis.get("strengths", []),
        improvements=analysis.get("improvements", []),
        missing_points=analysis.get("missing_points", []),
        overall_score=analysis.get("overall_score", 0),
        improved_answer=analysis.get("improved_answer", ""),
        next_question_topic="architecture" if session.topic == "requirements" else "requirements"
    )