import streamlit as st
import google.generativeai as genai
import datetime
import os

# 1. 페이지 설정 (가장 먼저 실행)
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
except Exception as e:
    st.error("🚨 API 키 오류: secrets.toml 파일을 확인해주세요.")
    st.stop()

# 3. [중요] 변수 정의 (에러 방지용)
usage_keys = [
    "log_lite", "log_flash", "log_pro",
    "spec_lite", "spec_flash", "spec_pro",
    "os_lite", "os_flash", "os_pro"
]

# 4. 사용량 카운터 함수
@st.cache_resource
def get_shared_usage_stats():
    stats_init = {key: 0 for key in usage_keys}
    return {
        'date': str(datetime.date.today()),
        'stats': stats_init
    }

shared_data = get_shared_usage_stats()
today_str = str(datetime.date.today())

if shared_data['date'] != today_str:
    shared_data['date'] = today_str
    for key in usage_keys:
        shared_data['stats'][key] = 0

# 5. 초기화 함수들
def clear_log_input():
    st.session_state["raw_log_area"] = ""

def clear_analysis_input():
    st.session_state["log_analysis_area"] = ""

def clear_spec_input():
    st.session_state["input_spec"] = ""

def clear_os_input():
    st.session_state["os_model"] = ""
    st.session_state["os_ver"] = ""

# 6. 사이드바 설정
with st.sidebar:
    st.header("🤖 엔진 설정")
    selected_model_name = st.selectbox(
        "AI 모델 선택:",
        ("Gemini 2.5 Flash Lite (가성비)", "Gemini 2.5 Flash (표준)", "Gemini 3 Flash Preview (최신)")
    )
    
    if "Lite" in selected_model_name: 
        MODEL_ID = "models/gemini-2.5-flash-lite"
        current_model_type = "lite"
    elif "Gemini 3" in selected_model_name: 
        MODEL_ID = "models/gemini-3-flash-preview"
        current_model_type = "pro"
    else: 
        MODEL_ID = "models/gemini-2.5-flash"
        current_model_type = "flash"

    st.success(f"선택됨: {selected_model_name}")
    st.markdown("---")
    st.markdown("### 📊 일일 사용량")
    
    # 간단한 카운터 표시
    log_cnt = shared_data['stats'][f"log_{current_model_type}"]
    spec_cnt = shared_data['stats'][f"spec_{current_model_type}"]
    os_cnt = shared_data['stats'][f"os_{current_model_type}"]
    
    st.write(f"🔹 로그 분석: {log_cnt}회")
    st.write(f"🔹 스펙 조회: {spec_cnt}회")
    st.write(f"🔹 OS 추천: {os_cnt}회")

# 7. AI 호출 함수
def get_gemini_response(prompt, current_api_key, func_prefix):
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(prompt)
        count_key = f"{func_prefix}_{current_model_type}"
        shared_data['stats'][count_key] += 1
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ========================================================
# 메인 화면
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# [TAB 0] 로그 분류 (모바일 업로드 최적화)
with tab0:
    st.header("⚡ 로그 자동 분류")
    st.caption("파일을 올리거나 텍스트를 붙여넣으세요.")

    # 폼(Form) 사용: 모바일 끊김 방지
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택", type=["txt", "log", "out", "cfg", "csv"])
        raw_log_input = st.text_area("📝 또는 로그 붙여넣기:", height=150, key="raw_log_area")
        submitted = st.form_submit_button("🚀 분류 실행")

    st.button("🗑️ 지우기", on_click=clear_log_input, key="clr_0")

    if submitted:
        final_log = ""
        # 파일 읽기 로직 (인코딩 자동 감지)
        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            try:
                final_log = bytes_data.decode("utf-8")
            except:
                try:
                    final_log = bytes_data.decode("cp949")
                except:
                    final_log = bytes_data.decode("utf-8", errors="ignore")
            st.success(f"파일 로드 성공: {uploaded_file.name}")
        elif raw_log_input:
            final_log = raw_log_input

        if not final_log:
            st.warning("내용이 없습니다.")
        else:
            with st.spinner("분석 중..."):
                prompt = f"""
                당신은 Cisco 엔지니어입니다. 로그를 분석하여 Critical, Warning, Info로 분류하고 
                핵심 내용만 요약하세요. (전체 리스트 출력 금지)
                
                [입력 로그]
                {final_log}
                """
                res = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.session_state['res_class'] = res
                st.session_state['log_buf'] = final_log

    if 'res_class' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state['res_class'])
        if st.button("📝 정밀 분석 탭으로 복사"):
            st.session_state['log_transfer'] = st.session_state.get('log_buf', "")
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# [TAB 1] 정밀 분석 (RCA)
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (Root Cause)")
    val = st.session_state.get('log_transfer', "")
    log_in = st.text_area("로그 입력:", value=val, height=200, key="log_analysis_area")
    
    if st.button("🚀 정밀 분석 실행", key="btn_1"):
        if log_in:
            with st.spinner("분석 중..."):
                prompt = f"""
                Cisco Tier 3 엔지니어로서 로그의 근본 원인(Root Cause)과 해결책(CLI)을 제시하세요.
                [로그] {log_in}
                """
                st.markdown(get_gemini_response(prompt, API_KEY_LOG, 'log'))

# [TAB 2] 스펙 조회
with tab2:
    st.header("장비 스펙 조회")
    model_in = st.text_input("모델명 (예: C9300-48P)", key="input_spec")
    if st.button("조회 실행", key="btn_2"):
        if model_in:
            with st.spinner("검색 중..."):
                prompt = f"{model_in}의 하드웨어 스펙(Port, CPU, Power 등)을 표로 정리하세요."
                st.markdown(get_gemini_response(prompt, API_KEY_SPEC, 'spec'))

# [TAB 3] OS 추천
with tab3:
    st.header("OS 추천")
    fam = st.radio("계열:", ("Catalyst", "Nexus"), horizontal=True)
    os_mod = st.text_input("모델명", key="os_model")
    os_ver = st.text_input("현재 버전", key="os_ver")
    
    if st.button("OS 분석 실행", key="btn_3"):
        if os_mod:
            with st.spinner("검색 중..."):
                prompt = f"""
                {fam} 장비 ({os_mod})의 추천 OS 버전(Gold Star/MD)을 HTML 테이블로 출력하세요.
                현재 버전: {os_ver}
                """
                st.markdown(get_gemini_response(prompt, API_KEY_OS, 'os'), unsafe_allow_html=True)
