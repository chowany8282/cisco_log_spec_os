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
    st.error("🚨 **API 키를 찾을 수 없습니다.**\n\n`.streamlit/secrets.toml` 파일에 API 키가 올바르게 저장되어 있는지 확인해주세요.")
    st.stop()

# ========================================================
# 💾 사용량 카운터 설정
# ========================================================
usage_keys = ["log_cnt", "spec_cnt", "os_cnt"]

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
    
    # 모델 선택 메뉴
    selected_model_name = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
        (
            "Gemini 2.5 Flash (추천: 표준/균형)", 
            "Gemini 2.5 Lite (초고속/무료량 많음)",
            "Gemini 3.0 Pro (최신/고성능)"
        )
    )
    
    # 모델 ID 매핑
    if "2.5 Lite" in selected_model_name:
        MODEL_ID = "models/gemini-2.5-flash-lite"
    elif "3.0 Pro" in selected_model_name:
        MODEL_ID = "models/gemini-3.0-flash" 
    else: 
        MODEL_ID = "models/gemini-2.5-flash"

    st.success(f"선택됨: {selected_model_name}")
    st.caption(f"ID: {MODEL_ID}")
    
    st.markdown("---")
    st.markdown("### 📊 일일 누적 사용량")
    st.caption(f"📅 {today_str} 기준")

    # 카운터 표시
    log_c = shared_data['stats']['log_cnt']
    spec_c = shared_data['stats']['spec_cnt']
    os_c = shared_data['stats']['os_cnt']

    st.text(f"📊 로그 분석: {log_c}회")
    st.text(f"🔍 스펙 조회: {spec_c}회")
    st.text(f"💿 OS 추천:  {os_c}회")

    st.markdown("---")
    st.markdown("Created by Wan Hee Cho")

# ========================================================
# 🤖 AI 연결 및 에러 처리 함수 (핵심 수정!)
# ========================================================
def get_gemini_response(prompt, current_api_key, func_prefix):
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(prompt)
        
        # 성공 시 카운트 증가
        count_key = f"{func_prefix}_cnt"
        shared_data['stats'][count_key] += 1
        
        return response.text

    except Exception as e:
        error_msg = str(e)
        
        # 🚨 에러 메시지 '통역' 로직
        if "429" in error_msg or "Quota" in error_msg or "ResourceExhausted" in error_msg:
            return f"""
            ### ⛔ **일일 무료 사용량 초과 (Quota Exceeded)**
            
            오늘 할당된 무료 사용량을 모두 소진했습니다.
            
            **💡 해결 방법:**
            1. 사이드바에서 모델을 **'Gemini 2.5 Lite'**로 변경해 보세요. (더 적은 자원을 소모합니다)
            2. 잠시 기다렸다가 다시 시도해 주세요.
            """
        
        elif "404" in error_msg or "Not Found" in error_msg:
            return f"""
            ### ❌ **모델을 찾을 수 없음 (Model Not Found)**
            
            선택하신 모델(`{MODEL_ID}`)을 현재 사용할 수 없습니다.
            
            **💡 해결 방법:**
            * 사이드바에서 **'Gemini 2.5 Flash'** 같은 다른 모델을 선택해 주세요.
            """
            
        elif "API key" in error_msg or "403" in error_msg:
            return f"""
            ### 🔑 **API 키 오류 (Auth Error)**
            
            API 키가 올바르지 않거나 권한이 없습니다.
            `secrets.toml` 파일의 API 키를 다시 확인해 주세요.
            """
            
        elif "500" in error_msg or "Internal" in error_msg:
            return f"""
            ### 🔥 **구글 서버 오류 (Server Error)**
            
            일시적인 구글 서버 문제입니다.
            잠시 후 다시 버튼을 눌러주세요.
            """
            
        else:
            # 그 외 알 수 없는 에러
            return f"""
            ### 🚨 **알 수 없는 오류 발생**
            
            **에러 내용:**
            ```
            {error_msg}
            ```
            잠시 후 다시 시도하거나, 모델을 변경해 보세요.
            """

# ========================================================
# 🖥️ 메인 화면 구성
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 특이 로그 선별 (Anomaly)", "📊 로그 정밀 분석", "🔍 하드웨어 스펙", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 선별기
# ========================================================
with tab0:
    st.header("⚡ 특이 로그 정밀 추출 (Significant Anomalies)")
    st.caption("일상적인 로그는 모두 제거하고, **분석 가치가 있는 '특이 사항'**만 골라냅니다.")
    
    uploaded_file = st.file_uploader("📂 로그 파일 업로드 (txt, log)", type=["txt", "log"])
    raw_log_input = st.text_area("📝 또는 여기에 로그를 직접 붙여넣으세요:", height=200, key="raw_log_area")
    
    col_btn1, col_btn2 = st.columns([1, 6])
    with col_btn1:
        run_btn = st.button("AI 선별 실행", key="btn_classify")
    with col_btn2:
        st.button("🗑️ 입력창 지우기", on_click=clear_log_input, key="clr_class")

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
            with st.spinner(f"🤖 AI({MODEL_ID.split('/')[-1]})가 '특이 사항'만 정밀 분석 중..."):
                prompt = f"""
                당신은 Cisco 로그 분석 전문가입니다.
                제공된 로그에서 **'통상적인 운영 로그'는 배제**하고, **엔지니어의 분석이 필요한 '특이 사항(Anomaly)'**만 추출하세요.

                [필터링 기준]
                1. **제외 대상 (출력 금지):**
                   - Link Up/Down (단순 포트 문제), Config 저장
                   - 날짜/시간이 없는 텍스트, 일반적인 Info/Notice
                2. **포함 대상 (특이 사항):**
                   - System: Traceback, Crash, Watchdog, Unexpected exception
                   - Hardware: Parity Error, ECC Error, ASIC Fail
                   - Resource: Malloc Fail, CPU Hog, Memory Leak
                   - Network: Storm Control, BPDU Guard, Mac Flapping
                3. **중복 압축:** 동일한 로그는 1개로 합치고 (총 N회 발생) 표기.

                [출력 레이아웃]
                - **로그 코드 블록(Code Block)을 무조건 맨 위**에 배치하세요.
                - 설명은 코드 블록 **아래**에 '└─' 기호를 써서 적으세요.

                [입력 데이터]
                {final_log_content}

                [출력 형식 예시]
                ### 🚨 시스템 치명적 오류 (System Critical)
                
                **1. 프로세스 크래시 (총 1회 발생)**
                ```
                2024 Jan 31 21:03:03 %SYS-2-MALLOCFAIL: Memory allocation failed...
                ```
                └─ (설명) 메모리 할당 실패로 인한 프로세스 종료.

                ### ⚠️ 비정상 네트워크 동작
                
                **1. 스톰 컨트롤 감지 (총 50회 발생)**
                ```
                2024 Jan 31 22:00:00 %STORM_CONTROL-3-FILTERED: Broadcast storm detected
                ```
                └─ (설명) 브로드캐스트 스톰 발생. 루핑 점검 필요.
                """
                classified_result = get_gemini_response(prompt, API_KEY_OS, 'os')
                st.session_state['classified_result'] = classified_result 
                
    if 'classified_result' in st.session_state:
        st.markdown("---")
        
        # 전체 복사 버튼
        col_copy_btn, col_copy_msg = st.columns([2, 5])
        with col_copy_btn:
            if st.button("📝 선별된 로그 전체 복사 (정밀 분석용)"):
                 st.session_state['log_transfer'] = st.session_state['classified_result']
                 st.success("✅ 복사 완료! 상단의 '📊 로그 정밀 분석' 탭으로 이동하세요.")
        
        st.subheader("🎯 AI 선별 결과 (System Anomalies)")
        st.markdown(st.session_state['classified_result'])

# ========================================================
# [TAB 1] 로그 분석기
# ========================================================
with tab1:
    st.header("로그 분석 및 장애 진단")
    default_log_value = st.session_state.get('log_transfer', "")
    log_input = st.text_area("분석할 로그를 입력하세요:", value=default_log_value, height=150, key="log_analysis_area")
    
    c1, c2 = st.columns([1, 6])
    with c1:
        btn_run_log = st.button("로그 분석 실행", key="btn_log")
    with c2:
        st.button("🗑️ 입력창 지우기", on_click=clear_analysis_input, key="clr_anal")

    if btn_run_log:
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"AI가 로그를 분석 중입니다..."):
                prompt = f"""
                당신은 시스코 전문가입니다. 
                아래 제공된 로그를 분석하고 다음 형식으로 답하세요.
                
                로그: 
                {log_input}
                
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
                if "Nexus" in device_family:
                    family_prompt = "당신은 Cisco Nexus(NX-OS) 전문가입니다. 반드시 **NX-OS 버전**만 추천하세요."
                    search_keyword = "Nexus"
                else:
                    family_prompt = "당신은 Cisco Catalyst(IOS-XE) 전문가입니다. 반드시 **IOS-XE 버전**만 추천하세요."
                    search_keyword = "Catalyst"

                current_ver_query = f"Cisco {search_keyword} {os_model} {os_ver if os_ver else ''} Last Date of Support"
                current_ver_url = f"https://www.google.com/search?q={current_ver_query.replace(' ', '+')}"

                prompt = f"""
                {family_prompt}
                다음 장비의 **OS 소프트웨어**를 분석하여 **HTML Table** 코드로 출력하세요.

                [필수 지침]
                1. 오직 HTML 코드만 출력하세요. 
                2. 테이블 스타일: <table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>

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
                response_html = response_html.replace("```html", "").replace("```", "")
                
                st.markdown(response_html, unsafe_allow_html=True)
