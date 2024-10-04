import json
import boto3
import os
from newsapi import NewsApiClient
from dotenv import load_dotenv
from textblob import TextBlob
from decimal import Decimal  # Добавляем модуль для работы с Decimal

# Загрузка переменных окружения из .env файла
load_dotenv()

# Инициализация клиента STS
sts_client = boto3.client('sts', region_name=os.getenv('AWS_REGION'))

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

    for article in articles:
        try:
            # Анализ тональности описания новости
            description = article.get('description', '')
            analysis = TextBlob(description)
            sentiment = Decimal(str(analysis.sentiment.polarity))  # Преобразование float в Decimal

            # Определение компании из заголовка или описания
            company = extract_company(article.get('title', ''), description)

            # Сохранение данных в DynamoDB
            table.put_item(
                Item={
                    'company': company,
                    'headline': article.get('title', ''),
                    'description': description,
                    'sentiment': sentiment,  # Используем Decimal
                    'url': article.get('url', ''),
                    'source': article['source'].get('name', 'Unknown'),
                    'publishedAt': article.get('publishedAt', ''),
                    'author': article.get('author', 'Unknown')
                }
            )
            print(f"Записано: {article.get('title', '')}")

        except Exception as e:
            print(f"Ошибка при записи новости в DynamoDB: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps('Новости успешно обработаны')
    }

def extract_company(title, description):
    """
    Функция для определения компании из заголовка или описания.
    Простой пример для нахождения компаний в тексте.
    """
    companies = ['Tesla', 'Apple', 'Google', 'Amazon', 'Microsoft', 'Facebook', 'Netflix', 'Nvidia']  # Пример списка компаний
    for company in companies:
        if company.lower() in title.lower() or company.lower() in description.lower():
            return company
    return 'Unknown'

if __name__ == "__main__":
    # Можем запустить локально для теста
    lambda_handler({}, {})
