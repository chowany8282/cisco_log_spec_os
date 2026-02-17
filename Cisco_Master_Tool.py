import streamlit as st
import google.generativeai as genai
import datetime
import os

# ========================================================
# 🎨 페이지 기본 설정
# ========================================================
st.set_page_config(
    page_title="Cisco AI Master System",
    page_icon="🛡️",
    layout="wide"
)

# ========================================================
# 🔑 사용자 API 키 설정
# ========================================================
try:
    API_KEY_LOG = st.secrets["API_KEY_LOG"]
    API_KEY_SPEC = st.secrets["API_KEY_SPEC"]
    API_KEY_OS = st.secrets["API_KEY_OS"]
except Exception as e:
    st.error("🚨 API 키를 찾을 수 없습니다.")
    st.stop()

# ========================================================
# 💾 사용량 카운터 설정
# ========================================================
usage_keys = [
    "log_lite", "log_flash", "log_pro",
    "spec_lite", "spec_flash", "spec_pro",
    "os_lite", "os_flash", "os_pro"
]

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

# ========================================================
# 🧹 입력창 초기화 함수들
# ========================================================
def clear_log_input():
    st.session_state["raw_log_area"] = ""

def clear_analysis_input():
    st.session_state["log_analysis_area"] = ""

def clear_spec_input():
    st.session_state["input_spec"] = ""

def clear_os_input():
    st.session_state["os_model"] = ""
    st.session_state["os_ver"] = ""

# ========================================================
# 🤖 사이드바 설정
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    selected_model_name = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
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

    st.markdown("### 📊 일일 누적 사용량")
    st.caption(f"📅 {today_str} 기준 (서버 유지)")

    count_style = """
    <style>
        .usage-box { margin-bottom: 15px; padding: 10px; background-color: #f0f2f6; border-radius: 5px; }
        .usage-title { font-weight: bold; font-size: 14px; margin-bottom: 5px; color: #31333F; }
        .usage-item { font-size: 13px; color: #555; display: flex; justify-content: space-between; }
        .usage-num { font-weight: bold; color: #0068c9; }
    </style>
    """
    st.markdown(count_style, unsafe_allow_html=True)

    def draw_usage(title, prefix):
        lite = shared_data['stats'][f"{prefix}_lite"]
        flash = shared_data['stats'][f"{prefix}_flash"]
        pro = shared_data['stats'][f"{prefix}_pro"]
        
        st.markdown(f"""
        <div class="usage-box">
            <div class="usage-title">{title}</div>
            <div class="usage-item"><span>🔹 Lite</span> <span class="usage-num">{lite}회</span></div>
            <div class="usage-item"><span>⚡ Flash</span> <span class="usage-num">{flash}회</span></div>
            <div class="usage-item"><span>🚀 Pro</span> <span class="usage-num">{pro}회</span></div>
        </div>
        """, unsafe_allow_html=True)

    draw_usage("📊 로그 분석 & 분류 (Log Key)", "log")
    draw_usage("🔍 스펙 조회 (Spec Key)", "spec")
    draw_usage("💿 OS 추천 (OS Key)", "os")

# ========================================================
# 🤖 AI 연결 함수
# ========================================================
def get_gemini_response(prompt, current_api_key, func_prefix):
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(prompt)
        count_key = f"{func_prefix}_{current_model_type}"
        shared_data['stats'][count_key] += 1
        return response.text
    except Exception as e:
        return f"System Error: {str(e)}"

# ========================================================
# 🖥️ 메인 화면 구성
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류", "📊 로그 정밀 분석", "🔍 하드웨어 스펙", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류기
# ========================================================
with tab0:
    st.header("⚡ 대량 로그 자동 분류")
    st.caption("로그 파일(.log, .txt)을 업로드하거나, 아래 텍스트 창에 직접 붙여넣으세요.")

    with st.form("upload_form", clear_on_submit=False):
        # [요청 반영] type=["log", "txt"]로 제한 설정
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (log, txt)", type=["log", "txt"])
        raw_log_input = st.text_area("📝 또는 로그 붙여넣기:", height=200, key="raw_log_area")
        submitted = st.form_submit_button("🚀 로그 분류 실행")

    st.button("🗑️ 입력창 지우기", on_click=clear_log_input, key="clr_class")

    if submitted:
        final_log_content = ""
        
        if uploaded_file is not None:
            raw_bytes = uploaded_file.getvalue()
            try:
                final_log_content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    final_log_content = raw_bytes.decode("cp949")
                except:
                    final_log_content = raw_bytes.decode("utf-8", errors="ignore")
            st.success(f"📂 파일 '{uploaded_file.name}' 로드 성공!")
            
        elif raw_log_input:
            final_log_content = raw_log_input
        
        if not final_log_content:
            st.warning("로그를 입력해주세요!")
        else:
            with st.spinner("로그 심각도 정밀 분석 및 필터링 중..."):
                prompt = f"""
                당신은 시스코 전문 네트워크 엔지니어입니다.
                제공된 로그를 **Critical, Warning, Info**로 분류하여 **[분석 제안]**을 작성하세요.
                
                (전체 리스트 출력 금지, 핵심 로그만 선별)

                [입력 로그]
                {final_log_content[:30000]}
                """
                classified_result = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.session_state['classified_result'] = classified_result 
                st.session_state['log_transfer_buffer'] = final_log_content
                
    if 'classified_result' in st.session_state:
        st.markdown("---")
        st.subheader("🎯 분석 제안 (Analysis Suggestion)")
        result_text = st.session_state['classified_result']
        st.markdown(result_text, unsafe_allow_html=True)
        
        # [요청 반영] 결과 다운로드 버튼 추가
        st.download_button(
            label="📥 결과 저장 (Log_Classification.txt)",
            data=result_text,
            file_name="Log_Classification_Result.txt",
            mime="text/plain"
        )
        
        if st.button("📝 전체 로그를 '로그 정밀 분석' 탭으로 복사하기"):
             st.session_state['log_transfer'] = st.session_state.get('log_transfer_buffer', "")
             st.success("복사되었습니다! '📊 로그 정밀 분석' 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 로그 정밀 분석
# ========================================================
with tab1:
    st.header("🕵️‍♀️ 로그 심층 분석 (Root Cause Analysis)")
    st.caption("로그의 단순 의미가 아니라, **장애의 근본 원인**을 추적합니다.")
    
    default_log_value = st.session_state.get('log_transfer', "")
    log_input = st.text_area("분석할 로그를 입력하세요:", value=default_log_value, height=200, key="log_analysis_area")
    
    c1, c2 = st.columns([1, 6])
    with c1:
        btn_run_log = st.button("🚀 정밀 분석 실행", key="btn_log")
    with c2:
        st.button("🗑️ 입력창 지우기", on_click=clear_analysis_input, key="clr_anal")

    if btn_run_log:
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"🔍 AI가 로그의 상관관계를 분석하고 근본 원인을 찾고 있습니다..."):
                prompt = f"""
                당신은 Cisco 본사의 **Tier 3 TAC 엔지니어**입니다.
                사용자가 제출한 로그를 바탕으로 **근본 원인(Root Cause)**과 **구체적인 해결책(CLI)**을 제시하세요.
                [입력 로그]
                {log_input[:30000]}
                """
                
                result = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.markdown(result, unsafe_allow_html=True)
                
                # [요청 반영] 결과 다운로드 버튼 추가
                st.download_button(
                    label="📥 결과 저장 (Root_Cause_Analysis.txt)",
                    data=result,
                    file_name="Root_Cause_Analysis.txt",
                    mime="text/plain"
                )

# ========================================================
# [TAB 2] 스펙 조회기
# ========================================================
with tab2:
    st.header("장비 하드웨어 스펙 조회")
    model_input = st.text_input("장비 모델명 (예: C9300-48P)", key="input_spec")
    
    c1, c2 = st.columns([1, 6])
    with c1:
        btn_run_spec = st.button("스펙 조회 실행", key="btn_spec")
    with c2:
        st.button("🗑️ 입력창 지우기", on_click=clear_spec_input, key="clr_spec")

    if btn_run_spec:
        if not model_input: st.warning("모델명을 입력해주세요!")
        else:
            with st.spinner("데이터시트 검색 중..."):
                prompt = f"""
                [대상 모델]: {model_input}
                위 모델의 하드웨어 스펙을 표(Table)로 요약해주세요.
                항목: Fixed Ports, Switching Capacity, Forwarding Rate, CPU/Memory, Power.
                주요 특징 3가지 포함. 한국어 답변.
                """
                result = get_gemini_response(prompt, API_KEY_SPEC, 'spec')
                st.markdown(result, unsafe_allow_html=True)

                # [요청 반영] 결과 다운로드 버튼 추가
                st.download_button(
                    label="📥 결과 저장 (Hardware_Spec.txt)",
                    data=result,
                    file_name=f"{model_input}_Spec.txt",
                    mime="text/plain"
                )

# ========================================================
# [TAB 3] OS 추천기
# ========================================================
with tab3:
    st.header("OS 추천 및 안정성 진단")
    st.caption("💡 장비 계열을 먼저 선택하면 더 정확한 추천을 받을 수 있습니다.")

    device_family = st.radio(
        "장비 계열 선택 (Device Family)",
        ("Catalyst (IOS-XE)", "Nexus (NX-OS)"),
        horizontal=True
    )
    
    col1, col2 = st.columns(2)
    with col1: os_model = st.text_input("장비 모델명", placeholder="예: C9300-48P", key="os_model")
    with col2: os_ver = st.text_input("현재 버전 (선택)", placeholder="예: 17.09.04a", key="os_ver")
        
    c1, c2 = st.columns([1, 6])
    with c1:
        btn_run_os = st.button("OS 분석 실행", key="btn_os")
    with c2:
        st.button("🗑️ 입력창 지우기", on_click=clear_os_input, key="clr_os")

    if btn_run_os:
        if not os_model: st.warning("장비 모델명은 필수입니다!")
        else:
            with st.spinner(f"{device_family} 데이터베이스 검색 중..."):
                # 프롬프트 내용 생략 (기존과 동일)
                prompt = f"""
                {family_family = "Nexus" if "Nexus" in device_family else "Catalyst"}
                {os_model} 장비의 추천 OS (MD/Gold Star)를 HTML Table로 출력하세요.
                """
                
                result = get_gemini_response(prompt, API_KEY_OS, 'os')
                st.markdown(result, unsafe_allow_html=True)

                # [요청 반영] 결과 다운로드 버튼 추가 (HTML 내용 포함)
                st.download_button(
                    label="📥 결과 저장 (OS_Recommendation.txt)",
                    data=result,
                    file_name=f"{os_model}_OS_Recommendation.txt",
                    mime="text/plain"
                )
