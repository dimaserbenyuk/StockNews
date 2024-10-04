import json
from lambda_function import lambda_handler

def test_event():
    # Пример пустого события для Lambda
    return {}

def test_context():
    # Пример пустого контекста для Lambda
    return {}

if __name__ == "__main__":
    event = test_event()
    context = test_context()
    response = lambda_handler(event, context)
    print("Response:", response)
