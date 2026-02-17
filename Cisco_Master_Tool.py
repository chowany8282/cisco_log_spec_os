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
    "os_lite", "os_flash", "os_pro",
    "class_lite", "class_flash", "class_pro"
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
# 🧹 [NEW] 입력창 초기화 함수
# ========================================================
def clear_log_input():
    st.session_state["raw_log_area"] = ""

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

    draw_usage("🚨 로그 분류 (Classify)", "class")
    draw_usage("📊 로그 분석 (Log Key)", "log")
    draw_usage("🔍 스펙 조회 (Spec Key)", "spec")
    draw_usage("💿 OS 추천 (OS Key)", "os")

    st.markdown("---")
    st.markdown("Created by Wan Hee Cho")

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

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류 (New)", "📊 로그 정밀 분석", "🔍 하드웨어 스펙", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류기 (수정됨: 초기화 버튼 + 제안 섹션 깔끔하게)
# ========================================================
with tab0:
    st.header("⚡ 대량 로그 자동 분류")
    st.caption("로그 파일을 업로드하거나, 아래 텍스트 창에 직접 붙여넣으세요.")
    
    uploaded_file = st.file_uploader("📂 로그 파일 업로드 (txt, log)", type=["txt", "log"])
    
    # 텍스트 입력창 (세션 상태와 연결하여 지우기 가능하도록 설정)
    raw_log_input = st.text_area("📝 또는 여기에 로그를 직접 붙여넣으세요:", height=200, key="raw_log_area")
    
    # 버튼 배치 (분류 실행 옆에 초기화 버튼)
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        run_btn = st.button("로그 분류 실행", key="btn_classify")
    with col_btn2:
        # [NEW] 초기화 버튼: 누르면 clear_log_input 함수 실행
        st.button("🗑️ 입력창 지우기", on_click=clear_log_input)

    if run_btn:
        final_log_content = ""
        if uploaded_file is not None:
            try:
                final_log_content = uploaded_file.getvalue().decode("utf-8")
                st.info(f"📂 업로드된 파일 '{uploaded_file.name}'을 분석합니다.")
            except Exception as e:
                st.error(f"파일 오류: {e}")
        elif raw_log_input:
            final_log_content = raw_log_input
        
        if not final_log_content:
            st.warning("로그를 입력해주세요!")
        else:
            with st.spinner("로그 심각도 분류 및 핵심 로그 추출 중..."):
                # [수정된 프롬프트] 분석 제안 섹션에 설명을 빼고 코드 블록만 출력하도록 지시
                prompt = f"""
                당신은 시스코 로그 분석 전문가입니다. 
                아래 로그를 [Critical, Warning, Info]로 분류하세요.
                
                [입력 로그]
                {final_log_content}

                [출력 형식]
                ### 🔴 Critical
                - (요약)
                
                ### 🟡 Warning
                - (요약)
                
                ### 🔵 Info
                - (요약)

                ---
                ### 🎯 분석 제안 (Analysis Suggestion)
                **정밀 분석이 반드시 필요한 핵심 로그**만 골라서 아래와 같이 출력하세요.
                **중요: 설명글이나 불렛포인트는 절대 쓰지 마세요.** 오직 로그 원본만 **코드 블록(```)** 안에 넣어서 출력하세요.
                (사용자가 버튼을 눌러 쉽게 복사할 수 있어야 합니다.)

                예시:
                ```
                %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet1/1 is down
                ```
                ```
                %TAHUSD-SLOT1-4-BUFFER_THRESHOLD_EXCEEDED: Module 1 buffer threshold exceeded
                ```
                """
                classified_result = get_gemini_response(prompt, API_KEY_LOG, 'class')
                st.session_state['classified_result'] = classified_result 
                st.session_state['log_transfer_buffer'] = final_log_content
                
    if 'classified_result' in st.session_state:
        st.markdown("---")
        st.subheader("📋 분류 결과")
        st.markdown(st.session_state['classified_result'])
        
        st.success("👆 [분석 제안]의 로그 우측 상단 'Copy' 아이콘을 누르면 복사됩니다!")
        
        if st.button("📝 전체 로그를 '로그 정밀 분석' 탭으로 복사하기"):
             st.session_state['log_transfer'] = st.session_state.get('log_transfer_buffer', "")
             st.success("복사되었습니다! '📊 로그 정밀 분석' 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 로그 분석기
# ========================================================
with tab1:
    st.header("로그 분석 및 장애 진단")
    default_log_value = st.session_state.get('log_transfer', "")
    log_input = st.text_area("분석할 로그를 입력하세요:", value=default_log_value, height=150, key="log_analysis_area")
    
    if st.button("로그 분석 실행", key="btn_log"):
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"AI가 로그를 분석 중입니다..."):
                prompt = f"""
                당신은 시스코 전문가입니다. 다음 로그를 분석하되, 반드시 아래 형식대로 답변하세요.
                로그: {log_input}
                답변 형식:
                [PART_1](발생 원인)
                [PART_2](네트워크 영향)
                [PART_3](조치 방법)
                """
                result = get_gemini_response(prompt, API_KEY_LOG, 'log')
                try:
                    p1 = result.split("[PART_1]")[1].split("[PART_2]")[0].strip()
                    p2 = result.split("[PART_2]")[1].split("[PART_3]")[0].strip()
                    p3 = result.split("[PART_3]")[1].strip()
                    st.subheader("🔴 발생 원인"); st.error(p1)
                    st.subheader("🟡 네트워크 영향"); st.warning(p2)
                    st.subheader("🟢 권장 조치"); st.success(p3)
                except: st.markdown(result)

# ========================================================
# [TAB 2] 스펙 조회기
# ========================================================
with tab2:
    st.header("장비 하드웨어 스펙 조회")
    model_input = st.text_input("장비 모델명 (예: C9300-48P)", key="input_spec")
    if st.button("스펙 조회 실행", key="btn_spec"):
        if not model_input: st.warning("모델명을 입력해주세요!")
        else:
            with st.spinner("데이터시트 검색 중..."):
                prompt = f"""
                [대상 모델]: {model_input}
                위 모델의 하드웨어 스펙을 표(Table)로 요약해주세요.
                항목: Fixed Ports, Switching Capacity, Forwarding Rate, CPU/Memory, Power.
                주요 특징 3가지 포함. 한국어 답변.
                """
                st.markdown(get_gemini_response(prompt, API_KEY_SPEC, 'spec'))

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
    with col1: os_model = st.text_input("장비 모델명", placeholder="예: C9300-48P or N9K-C93180YC-FX", key="os_model")
    with col2: os_ver = st.text_input("현재 버전 (선택)", placeholder="예: 17.09.04a or 10.2(3)", key="os_ver")
        
    if st.button("OS 분석 실행", key="btn_os"):
        if not os_model: st.warning("장비 모델명은 필수입니다!")
        else:
            with st.spinner(f"{device_family} 데이터베이스 검색 중..."):
                if "Nexus" in device_family:
                    family_prompt = "당신은 Cisco Nexus(NX-OS) 전문가입니다. 반드시 **NX-OS 버전**만 추천하세요. IOS-XE 버전을 추천하면 절대 안 됩니다."
                    search_keyword = "Nexus"
                else:
                    family_prompt = "당신은 Cisco Catalyst(IOS-XE) 전문가입니다. 반드시 **IOS-XE 버전**만 추천하세요. NX-OS 버전을 추천하면 절대 안 됩니다."
                    search_keyword = "Catalyst"

                current_ver_query = f"Cisco {search_keyword} {os_model} {os_ver if os_ver else ''} Last Date of Support"
                current_ver_url = f"[https://www.google.com/search?q=](https://www.google.com/search?q=){current_ver_query.replace(' ', '+')}"

                prompt = f"""
                {family_prompt}
                다음 장비의 **OS 소프트웨어**를 분석하여 **HTML Table** 코드로 출력하세요.

                [필수 지침]
                1. 오직 HTML 코드만 출력하세요. (마크다운 X)
                2. 링크는 <a href='URL' target='_blank'> 형식을 사용하세요.
                3. 테이블 스타일: <table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>

                [분석 내용]
                - MD 및 Gold Star 버전 최우선 추천.
                - 안정성 등급 별점(⭐⭐⭐⭐⭐) 표시.

                [대상 장비]: {os_model} ({device_family})
                [현재 OS 버전]: {os_ver if os_ver else '정보 없음'}
                [검증 링크]: {current_ver_url}

                <h3>1. 현재 버전 상태</h3>
                <table>...</table>
                <br>
                <h3>2. 추천 OS (Recommended Releases)</h3>
                <table>...</table>
                """
                
                response_html = get_gemini_response(prompt, API_KEY_OS, 'os')
                st.markdown(response_html, unsafe_allow_html=True)
