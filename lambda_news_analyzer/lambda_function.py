import json
import boto3
import os
import re
from newsapi import NewsApiClient
from dotenv import load_dotenv
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from decimal import Decimal
import spacy
from fuzzywuzzy import process

# Загрузка модели spaCy
nlp = spacy.load("en_core_web_sm")

# Загрузка переменных окружения из .env файла
load_dotenv()

# Инициализация клиента STS
sts_client = boto3.client('sts', region_name=os.getenv('AWS_REGION'))

# Загрузка данных о компаниях из файла
with open('companies.json', 'r') as f:
    COMPANIES = json.load(f)

def lambda_handler(event, context):
    # Параметры запроса к News API
    query = 'stocks dividends'  # Поисковый запрос
    language = 'en'
    sort_by = 'publishedAt'  # Сортировка по дате публикации
    page_size = 100  # Максимальное количество статей за один запрос

    # Инициализация NewsApiClient с использованием API ключа из переменных окружения
    newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))

    try:
        # Получение новостей через NewsApiClient
        all_articles = newsapi.get_everything(
            q=query,
            language=language,
            sort_by=sort_by,
            page_size=page_size
        )
    except Exception as e:
        print(f"Ошибка при получении новостей: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Ошибка при получении новостей')
        }

    articles = all_articles.get('articles', [])

    # Принятие роли через STS
    try:
        assumed_role = sts_client.assume_role(
            RoleArn=os.getenv('ROLE_ARN'),  # ARN вашей роли STS
            RoleSessionName='LambdaNewsAnalyzerSession'
        )
        
        credentials = assumed_role['Credentials']
        
        # Инициализация клиента DynamoDB с временными креденшиалами
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        
        table = dynamodb.Table(os.getenv('DYNAMODB_TABLE'))
    except Exception as e:
        print(f"Ошибка при принятии роли STS: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Ошибка при настройке доступа к DynamoDB')
        }

    # Инициализация анализатора настроений VADER
    vader_analyzer = SentimentIntensityAnalyzer()

    # Использование batch_writer для эффективной пакетной записи
    with table.batch_writer() as batch:
        for article in articles:
            try:
                # Анализ тональности описания новости с помощью TextBlob
                description = article.get('description', '')
                textblob_analysis = TextBlob(description)
                textblob_sentiment = Decimal(str(textblob_analysis.sentiment.polarity))  # Преобразование float в Decimal

                # Анализ тональности описания новости с помощью VADER
                vader_scores = vader_analyzer.polarity_scores(description)
                vader_sentiment = Decimal(str(vader_scores['compound']))  # Используем 'compound' как общий показатель настроения

                # Извлечение названия компании
                title = article.get('title', '')
                company = extract_company(title, description)

                # Сохранение данных в DynamoDB
                item = {
                    'company': company,
                    'headline': title,
                    'description': description,
                    'textblob_sentiment': textblob_sentiment,  # Добавляем показатель настроения TextBlob
                    'vader_sentiment': vader_sentiment,        # Добавляем показатель настроения VADER
                    'url': article.get('url', ''),
                    'source': article['source'].get('name', 'Unknown'),
                    'publishedAt': article.get('publishedAt', ''),
                    'author': article.get('author', 'Unknown')
                }

                batch.put_item(Item=item)
                print(f"Записано: {title}")

            except Exception as e:
                print(f"Ошибка при записи новости в DynamoDB: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps('Новости успешно обработаны')
    }

def extract_company(title, description):
    """
    Функция для определения компании из заголовка или описания.
    Использует извлечение тикеров, NER и нечёткое сопоставление.
    """
    # Поиск тикеров в заголовке
    ticker_pattern = r'\((?:NASDAQ|NYSE|OTCMKTS):([A-Z]+)\)'
    tickers = re.findall(ticker_pattern, title)
    
    for ticker in tickers:
        company = COMPANIES.get(ticker)
        if company:
            return company
    
    # Используем NER для извлечения организаций
    combined_text = f"{title} {description}"
    doc = nlp(combined_text)
    entities = [ent.text for ent in doc.ents if ent.label_ == "ORG"]

    # Проверка с помощью точного и нечёткого сопоставления
    for entity in entities:
        # Точное сопоставление
        for ticker, company in COMPANIES.items():
            if company.lower() in entity.lower():
                return company
        # Нечёткое сопоставление
        match, score = process.extractOne(entity, COMPANIES.values())
        if score >= 90:  # Порог точности, можно настроить
            return match
    
    # Если NER не дал результатов, используем нечёткое сопоставление по всему тексту
    all_companies = list(COMPANIES.values())
    match, score = process.extractOne(combined_text, all_companies)
    if score >= 80:  # Порог точности, можно настроить
        return match
    
    return 'Unknown'

if __name__ == "__main__":
    # Можем запустить локально для теста
    lambda_handler({}, {})
