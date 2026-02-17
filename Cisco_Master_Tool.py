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
# 🤖 사이드바 설정 (모델 메뉴 수정됨)
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    
    # [수정] 모델 선택 리스트에 '1.5 Flash' 추가
    selected_model_name = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
        (
            "Gemini 1.5 Flash (안정성/로그분석 추천)",  # 추가됨
            "Gemini 2.0 Flash (최신/균형)",
            "Gemini 2.0 Flash Lite (초고속/가성비)"
        )
    )
    
    # [수정] 모델 매핑 로직 (정확한 ID 연결)
    if "1.5 Flash" in selected_model_name: 
        MODEL_ID = "models/gemini-1.5-flash"
        current_model_type = "flash"
    elif "2.0 Flash Lite" in selected_model_name: 
        MODEL_ID = "models/gemini-2.0-flash-lite-preview-02-05" # 최신 라이트 버전
        current_model_type = "lite"
    else: 
        MODEL_ID = "models/gemini-2.0-flash" # 기본 2.0 Flash
        current_model_type = "pro" # 편의상 pro 카운터로 분류

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

    draw_usage("📊 로그 분석 (Log Key)", "log")
    draw_usage("🔍 스펙 조회 (Spec Key)", "spec")
    draw_usage("💿 OS 추천 & 선별 (OS Key)", "os")

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
            with st.spinner("🤖 AI가 '통상적인 로그'를 제거하고 '특이 사항'만 추출 중..."):
                prompt = f"""
                당신은 Cisco 로그 분석의 최종 권위자입니다.
                제공된 로그에서 **'통상적인 운영 로그'는 완벽히 배제**하고, **엔지니어의 분석이 필요한 '특이 사항(Anomaly)'**만 정밀 추출하세요.

                [엄격한 필터링 기준]
                1. **완벽 제거 대상 (Whitelist - 절대 출력 금지):**
                   - Link Up/Down, Interface Flapping, Error-Disable (단순 포트 문제)
                   - Config 저장, 로그인 이력, NTP/SNMP 메시지
                   - OSPF/BGP/EIGRP 단순 Neighbor Change (Up/Down)
                   - 일반적인 Info/Notice/Warning
                2. **반드시 포함 대상 (Blacklist - 특이 사항):**
                   - **System Integrity:** `Traceback`, `Crash`, `Stack dump`, `Watchdog`, `Unexpected exception`
                   - **Hardware Fatal:** `Parity Error`, `ECC Error`, `Uncorrectable Error`, `ASIC Fail`
                   - **Resource Critical:** `Malloc Fail`, `CPU Hog`, `Process Crash`, `Memory Leak`
                   - **Security/Stability:** `Storm Control`, `BPDU Guard`, `Mac Flapping` (대량 발생 시), `Duplicate IP`
                3. **요약:** 동일한 특이 로그는 1개로 압축하고 (총 N회 발생)으로 표기.

                [출력 레이아웃]
                - **로그 코드 블록(Code Block)을 무조건 맨 위**에 배치하세요.
                - 설명은 코드 블록 **아래**에 '└─' 기호를 써서 간략히 적으세요.

                [입력 데이터]
                {final_log_content}

                [출력 형식 예시]
                ### 🚨 시스템 치명적 오류 (System Critical)
                
                **1. 프로세스 크래시 및 트레이스백 (총 1회 발생)**
                ```
                2024 Jan 31 21:03:03 %SYS-2-MALLOCFAIL: Memory allocation of 65536 bytes failed... (Traceback...)
                ```
                └─ (설명) 메모리 할당 실패로 인한 시스템 프로세스 종료.

                ### ⚠️ 비정상 네트워크 동작 (Network Anomaly)
                
                **1. 스톰 컨트롤 동작 감지 (총 50회 발생)**
                ```
                2024 Jan 31 22:00:00 %STORM_CONTROL-3-FILTERED: A Broadcast storm detected on Et1/1
                ```
                └─ (설명) 브로드캐스트 스톰 발생으로 인한 트래픽 차단 동작. 루핑 점검 필요.
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
                아래 제공된 로그(또는 로그 리스트)를 정밀 분석하되, 반드시 아래 형식대로 답변하세요.
                
                로그: 
                {log_input}
                
                답변 형식:
                [PART_1](발생 원인 - 기술적 상세 분석)
                [PART_2](네트워크 영향)
                [PART_3](구체적인 조치 방법 및 명령어 제안)
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
