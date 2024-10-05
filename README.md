# StockNews

python3 -m venv venv
source venv/bin/activate


python -m pip install newsapi-python boto3 textblob spacy vaderSentiment

pip install fuzzywuzzy python-Levenshtein

python -m spacy download en_core_web_sm


python -m textblob.download_corpora 

aws dynamodb create-table \
    --table-name StockNews \
    --attribute-definitions AttributeName=headline,AttributeType=S \
    --key-schema AttributeName=headline,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5


aws dynamodb update-table \
    --table-name StockNews \
    --attribute-definitions \
        AttributeName=company,AttributeType=S \
        AttributeName=publishedAt,AttributeType=S \
    --global-secondary-index-updates \
        "[{\"Create\":{\"IndexName\": \"CompanyIndex\",\"KeySchema\":[{\"AttributeName\":\"company\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"publishedAt\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"},\"ProvisionedThroughput\":{\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}}}]"

pip install -r requirements.txt -t ./package
cd package
zip -r ../function.zip .
cd ..
zip -g function.zip lambda_function.py

python3 --version  

pyenv local 3.11.10

pyenv install 3.11.10
