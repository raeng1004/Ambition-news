import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.metanames import GenTextParamsMetaNames as GenParams
import os
from langdetect import detect



# IBM Watsonx AI API 설정
API_KEY = 'SOUcCBrKx0NmGvbCs114_4yxvAuaFOlAEkCyJDRK28q3'  # IBM Cloud API Key를 여기에 입력
PROJECT_ID = 'b08703d7-0a18-454a-9cc2-2aa5f1e929f8'  # IBM Project ID를 여기에 입력
NEWS_API_KEY = '73b17ead3cea453f9e12c3925f7c1f4d'  # NewsAPI 키를 여기에 입력


credentials = {
    "url": "https://us-south.ml.cloud.ibm.com",
    "apikey": API_KEY
}

# Watsonx AI로 요약 요청
def send_to_watsonxai(prompts,
                      model_name="meta-llama/llama-3-70b-instruct",
                      decoding_method="greedy",
                      max_new_tokens=300,
                      min_new_tokens=30,
                      temperature=1.0,
                      repetition_penalty=1.0,
                      stop_sequence=['\n\n']):
    try:
        model_params = {
            GenParams.DECODING_METHOD: decoding_method,
            GenParams.MIN_NEW_TOKENS: min_new_tokens,
            GenParams.MAX_NEW_TOKENS: max_new_tokens,
            GenParams.RANDOM_SEED: 42,
            GenParams.TEMPERATURE: temperature,
            GenParams.REPETITION_PENALTY: repetition_penalty,
        }

        model = Model(
            model_id=model_name,
            params=model_params,
            credentials=credentials,
            project_id=PROJECT_ID)

        response = model.generate_text(prompt=prompts[0])
        return response
    except Exception as e:
        print(f"Error during text generation: {e}")
        return "요약을 생성하는 중 오류가 발생했습니다."



# Watsonx AI를 사용하여 뉴스 기사를 요약하는 함수
def summarize_article(article_text):
    limited_text = " ".join(article_text.split()[:800])  # Watsonx에 전달할 텍스트를 800단어로 제한
    input_prompt = """
    위의 내용을 기반으로 한국어 요약을 작성해주세요.
    최대 3문장으로 작성해주세요.
    """
    prompt = f"""
    '''{limited_text}'''

    {input_prompt}
    """
    return send_to_watsonxai([prompt])



# Watsonx AI로 번역 요청 (Mistral Large 모델 사용)
def mistral_translate_text(english_title, english_summary, target_language='ko'):
    # Watsonx 모델로 번역 요청을 위한 프롬프트
    prompt = f"""

    Translate the following news article title and summary into natural and fluent Korean. The translation should reflect the original meaning, context, and tone, while accurately conveying professional terms, names, and specific expressions.

    Make sure the output is clearly divided into:
    1. Title: The title should be translated and separated from the summary.
    2. Summary: The summary should be translated, keeping the natural flow of the original text.

    Output format:
    - Title: [Translated title]
    - Summary: [Translated summary]

    """
    
    try:
        # Watsonx AI 모델을 사용해 번역 요청
        response = send_to_watsonxai([prompt], model_name="mistralai/mistral-large", max_new_tokens=300)

        # 응답 구조 확인을 위한 디버그 출력
        print("Watsonx AI 응답:", response)

        # 응답이 올바른지 확인
        if isinstance(response, dict):
            generated_text = response.get('generated_text', None)
            
            # 응답 내 'generated_text'가 있을 경우 처리
            if generated_text:
                # Watsonx 응답에서 "Title: "과 "Summary: "로 구분
                if "Title:" in generated_text and "Summary:" in generated_text:
                    title_part = generated_text.split("Title:")[1].split("Summary:")[0].strip()
                    summary_part = generated_text.split("Summary:")[1].strip()
                    return title_part, summary_part
                else:
                    raise ValueError("Could not split the title and summary.")
            else:
                raise ValueError("No 'generated_text' found in response.")
        else:
            raise ValueError("Invalid response structure from Watsonx AI.")
    
    except Exception as e:
        print(f"Error during translation: {e}")
        return english_title, english_summary  # 오류 발생 시 원본 텍스트 반환


    
# NewsAPI 키
API_KEY = '73b17ead3cea453f9e12c3925f7c1f4d'  


# 날짜 형식 변환 함수 (YYYY-MM-DD로 변환)
def format_date(date):
    return date.strftime('%Y-%m-%d')


# 입력된 키워드의 언어를 감지하여 한국어일 경우 영어로 번역하는 함수
def translate_keyword_if_needed(keyword):
    # 언어 감지: 입력된 키워드가 한국어일 경우 영어로 번역
    detected_language = detect(keyword)
    if detected_language == 'ko':  # 한국어일 경우 영어로 번역
        return GoogleTranslator(source='ko', target='en').translate(keyword)
    return keyword  # 이미 영어일 경우 번역하지 않고 그대로 반환

# NewsAPI를 통해 번역된 키워드로 뉴스 검색
def get_news_by_keyword(keyword, from_date, to_date):
    # 입력된 키워드를 영어로 번역(필요한 경우)
    translated_keyword = translate_keyword_if_needed(keyword)

    url = (
        f"https://newsapi.org/v2/everything?qInTitle={translated_keyword}&from={from_date}&to={to_date}"
        f"&sortBy=relevancy&language=en&pageSize=5&apiKey={API_KEY}"  # 영문 기사 / 관련성 기준 정렬 
    )
    response = requests.get(url)
    
    if response.status_code == 200:
        news_data = response.json()
        return news_data.get('articles', [])
    else:
        print(f"Error fetching news: {response.status_code}")
        return []

# 제외할 도메인 리스트
EXCLUDED_DOMAINS = ['yahoo.com', 'androidpolice.com']

# 특정 도메인 검사 함수
def is_excluded_domain(url):
    for domain in EXCLUDED_DOMAINS:
        if domain in url:
            return True
    return False

# BeautifulSoup을 사용하여 뉴스 본문 스크래핑
def extract_article_text(article_url):
    """
    주어진 URL에서 기사의 전체 본문을 추출하는 함수.
    """
     # 제외할 도메인 확인
    if is_excluded_domain(article_url):
        print(f"Skipping excluded domain: {article_url}")
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(article_url, headers=headers,timeout=10)
        response.raise_for_status()  # 요청에 실패하면 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # HTML 구조에서 <p> 태그 안에 본문이 포함됨
        paragraphs = soup.find_all('p')
        article_text = " ".join([p.get_text() for p in paragraphs])

        # 본문이 너무 짧으면 None을 반환
        if len(article_text.split()) < 50:
            return None
        
        return article_text
    except Exception as e:
        print(f"Error fetching article content from {article_url}: {e}")
        return None

# 뉴스 데이터를 사용자 언어로 번역하고 Watsonx로 요약하는 함수
def summarize_news_articles(articles, target_language):
    summarized_news = []
    for article in articles:
        title = article.get('title')
        url = article.get('url')

        # BeautifulSoup으로 스크래핑한 기사 원문을 가져오기
        article_text = extract_article_text(url)
        if article_text:
            summary = summarize_article(article_text)  # Watsonx AI 모델로 요약
        else:
            summary = article.get('description', 'No description available.')

        # GoogleTranslator로 제목만 번역
        try:
            translated_title = GoogleTranslator(source='auto', target=target_language).translate(title)
        except Exception as e:
            print(f"Title translation error: {e}")
            translated_title = title

        # Mistral 모델로 요약 번역
        try:
            translated_result = mistral_translate_text(title, summary, target_language)
            # 요약만 번역된 결과로 대체
            translated_summary = "\n".join(translated_result.split("\n")[1:])  # 번역된 요약
        except Exception as e:
            print(f"Summary translation error: {e}")
            translated_summary = summary

        summarized_news.append({
            'title': translated_title,
            'summary': translated_summary,
            'url': url,
            'source': article.get('source', {}).get('name'),
            'publishedAt': article.get('publishedAt'),
        })

    return summarized_news


