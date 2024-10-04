# from newsapi import NewsApiClient

# # Init
# newsapi = NewsApiClient(api_key='5f475c6c080344cdb1336d717941351d')

# # /v2/top-headlines - Используем country и category, без sources
# top_headlines = newsapi.get_top_headlines(q='apple',
#                                           category='business',
#                                           language='en',
#                                           country='us')

# print(top_headlines)
from newsapi import NewsApiClient

# Init
newsapi = NewsApiClient(api_key='5f475c6c080344cdb1336d717941351d')

# /v2/top-headlines
top_headlines = newsapi.get_top_headlines(q='bitcoin',
                                          sources='bbc-news,the-verge',
                                        #   category='business',
                                          language='en')
                                        #   country='us')

# # /v2/everything
# all_articles = newsapi.get_everything(q='bitcoin',
#                                       sources='bbc-news,the-verge',
#                                       domains='bbc.co.uk,techcrunch.com',
#                                       from_param='2017-12-01',
#                                       to='2017-12-12',
#                                       language='en',
#                                       sort_by='relevancy',
#                                       page=2)

# /v2/top-headlines/sources
sources = newsapi.get_sources()