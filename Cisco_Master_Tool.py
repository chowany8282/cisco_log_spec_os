import streamlit as st
import google.generativeai as genai
import datetime
import os
import io

# 1. 페이지 설정
st.set_page_config(
    page_title="Cisco AI Master System",
    page_icon="🛡️",
    layout="wide"
)

# 2. API 키 설정
try:
    API_KEY_LOG = st.secrets["API_KEY_LOG"]
    API_KEY_SPEC = st.secrets["API_KEY_SPEC"]
    API_KEY_OS = st.secrets["API_KEY_OS"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다.")
    st.stop()

# 3. 변수 초기화
usage_keys = ["log_lite", "log_flash", "log_pro", "spec_lite", "spec_flash", "spec_pro", "os_lite", "os_flash", "os_pro"]

@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {k: 0 for k in usage_keys}}

shared_data = get_shared_usage_stats()

# 4. 사이드바 & 모델 설정
with st.sidebar:
    st.header("🤖 엔진 설정")
    model_opt = st.selectbox("AI 모델:", ("Gemini 2.5 Flash Lite", "Gemini 2.5 Flash", "Gemini 3 Flash Preview"))
    
    if "Lite" in model_opt: MODEL_ID, m_type = "models/gemini-2.5-flash-lite", "lite"
    elif "Preview" in model_opt: MODEL_ID, m_type = "models/gemini-3-flash-preview", "pro"
    else: MODEL_ID, m_type = "models/gemini-2.5-flash", "flash"
    
    st.success(f"선택: {model_opt}")

def get_gemini_response(prompt, key, prefix):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(MODEL_ID)
        res = model.generate_content(prompt)
        shared_data['stats'][f"{prefix}_{m_type}"] += 1
        return res.text
    except Exception as e:
        return f"Error: {str(e)}"

# ========================================================
# 메인 화면
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# [TAB 0] 로그 분류 (확장자 제한 제거 버전)
with tab0:
    st.header("⚡ 로그 자동 분류")
    st.info("💡 모바일에서 파일 선택이 안 되면 '모든 파일' 보기로 선택하세요.")

    # [수정] type=None으로 설정하여 모든 파일 허용 (모바일 호환성 해결)
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (모든 형식 허용)", type=None)
        raw_log_input = st.text_area("📝 또는 로그 붙여넣기:", height=150)
        submitted = st.form_submit_button("🚀 분류 실행")

    if submitted:
        final_log = ""
        if uploaded_file:
            try:
                # 인코딩 자동 감지 시도
                bytes_data = uploaded_file.getvalue()
                try: final_log = bytes_data.decode("utf-8")
                except: final_log = bytes_data.decode("cp949", errors="ignore")
                st.success(f"파일 읽기 성공: {uploaded_file.name}")
            except Exception as e:
                st.error(f"파일 읽기 실패: {e}")
        elif raw_log_input:
            final_log = raw_log_input

        if final_log:
            with st.spinner("분석 중..."):
                prompt = f"""
                Cisco 엔지니어로서 로그를 Critical, Warning, Info로 분류하고 
                핵심 로그 원본과 간략한 설명을 제공하세요. (전체 리스트 출력 금지)
                [로그] {final_log[:30000]} 
                """
                res = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.session_state['res_class'] = res
                st.session_state['log_buf'] = final_log
        else:
            st.warning("파일을 선택하거나 내용을 입력하세요.")

    if 'res_class' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state['res_class'])
        if st.button("📝 정밀 분석 탭으로 복사", key="copy_btn"):
            st.session_state['log_transfer'] = st.session_state.get('log_buf', "")
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# [TAB 1] 정밀 분석
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    val = st.session_state.get('log_transfer', "")
    log_in = st.text_area("로그 입력:", value=val, height=200)
    if st.button("🚀 정밀 분석 실행"):
        if log_in:
            with st.spinner("분석 중..."):
                prompt = f"Cisco Tier 3 엔지니어 관점에서 근본 원인(Root Cause)과 해결책(CLI)을 제시하세요.\n[로그] {log_in[:30000]}"
                st.markdown(get_gemini_response(prompt, API_KEY_LOG, 'log'))

# [TAB 2] 스펙
with tab2:
    st.header("스펙 조회")
    m_in = st.text_input("모델명 (예: C9300)")
    if st.button("조회"):
        st.markdown(get_gemini_response(f"{m_in} 하드웨어 스펙 표로 정리", API_KEY_SPEC, 'spec'))

# [TAB 3] OS
with tab3:
    st.header("OS 추천")
    fam = st.radio("계열:", ("Catalyst", "Nexus"), horizontal=True)
    mod = st.text_input("모델명")
    if st.button("추천"):
        prompt = f"{fam} 장비 {mod} 추천 OS (MD/Gold Star) 테이블로 출력"
        st.markdown(get_gemini_response(prompt, API_KEY_OS, 'os'), unsafe_allow_html=True)
