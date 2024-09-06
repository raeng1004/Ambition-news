import streamlit as st
from datetime import datetime
import news8


# Streamlit 페이지 설정
st.set_page_config(page_title="전 세계 뉴스 통합검색 및 요약", layout="wide")

# 사이드바에서 날짜 선택
st.sidebar.header("뉴스 조회 기간 선택")
start_date = st.sidebar.date_input("시작 날짜", value=None)
end_date = st.sidebar.date_input("종료 날짜", value=None)

# 메인 화면에서 키워드 입력
st.title("전 세계 뉴스 통합검색 및 요약")
st.write("원하는 키워드를 입력하고, 관련 뉴스를 확인하세요.")

# 키워드 입력
keyword = st.text_input("키워드를 입력하세요:")
language_options = ['en', 'ko']
target_language = 'ko'  # 사용자 언어(한국어)


# 번역된 키워드를 통해 뉴스 검색
if st.button('뉴스 검색'):
    if keyword:
        if start_date and end_date:
            from_date = news8.format_date(start_date)
            to_date = news8.format_date(end_date)
            
            # 한국어 또는 영어로 입력된 키워드를 처리하여 뉴스 검색
            articles = news8.get_news_by_keyword(keyword, from_date, to_date)
            
            # Watsonx AI 모델을 통해 뉴스 기사 요약
            summarized_articles = news8.summarize_news_articles(articles, target_language)
            
            # 요약된 뉴스 데이터를 화면에 출력
            if summarized_articles:
                st.write(f"총 {len(summarized_articles)}개의 기사를 찾았습니다.")
                
                for idx, article in enumerate(summarized_articles):
                    st.subheader(f"{idx + 1}. {article['title']}")
                    st.write(f"출처: {article['source']}")
                    st.write(f"발행일: {article.get('publishedAt', '발행일 정보 없음')}")
                    st.text_area(label="요약", value=article['summary'], height=200, key=f"summary_{idx}")
                    st.write(f"[원문 보기]({article['url']})")
                st.write("---")
            else:
                st.write("관련 뉴스를 찾을 수 없습니다.")
        else:
            st.write("날짜를 선택해주세요.")
    else:
        st.write("키워드를 입력해주세요.")





        
