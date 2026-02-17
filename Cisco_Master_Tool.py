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
    st.caption("로그 파일을 업로드하거나, 아래 텍스트 창에 직접 붙여넣으세요.")

    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (모바일 호환)", type=None)
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

                [🚨 심각도 분류 기준 (Strict Rules)]
                1. **Critical (즉시 조치 필요)**:
                   - 장비 Crash, 모듈(Line card) Fail, Power Fail(이중화 깨짐)
                   - OSPF/BGP 등 주요 라우팅 프로토콜 Down
                   - Interface Down (단, admin down 제외)
                   - ⚠️ 'Smart License' 및 'Transceiver' 로그는 서비스 중단이 없다면 절대로 Critical로 분류하지 마세요.

                2. **Warning (관리 필요)**:
                   - **Smart License 관련 로그** (Authorization Failed, Expired 등) -> **무조건 Warning으로 분류**
                   - **Transceiver(SFP) 호환성 로그** (Unqualified, Not supported) -> **Warning 또는 Info로 분류**
                   - CPU/Memory 임계값 초과, 환경(온도/팬) 경고

                3. **Info (참고 정보)**:
                   - 단순 상태 변경 (Up/Down Flapping 제외), Config 변경, 로그인 기록
                   - 단순 SFP 삽입/제거 알림

                [출력 형식]
                전체 리스트는 생략하고, 분류된 **핵심 로그**만 아래 형식으로 출력하세요.
                
                ### 🔴 Critical (서비스 영향 있음)
                **1. (간략 설명) 모듈 1번 장애 발생**
                ```
                %MODULE-2-FAILED: Module 1 failed
                ```

                ### 🟡 Warning (잠재적 위험/라이선스)
                **1. (간략 설명) 스마트 라이선스 인증 실패**
                ```
                %SMART_LIC-3-AUTHORIZATION_FAILED: Your authorization has failed
                ```

                ### 🔵 Info (일반 알림)
                **1. (간략 설명) SFP 트랜시버 감지됨**
                ```
                %ETHPORT-5-IF_HARDWARE: Interface Ethernet1/1, hardware type changed to...
                ```

                [입력 로그]
                {final_log_content[:30000]}
                """
                classified_result = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.session_state['classified_result'] = classified_result 
                st.session_state['log_transfer_buffer'] = final_log_content
                
    if 'classified_result' in st.session_state:
        st.markdown("---")
        st.subheader("🎯 분석 제안 (Analysis Suggestion)")
        # [수정] unsafe_allow_html=True 추가하여 HTML 태그 적용
        st.markdown(st.session_state['classified_result'], unsafe_allow_html=True)
        
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
                당신은 Cisco 본사의 **Tier 3 TAC(Technical Assistance Center) 백본 엔지니어**입니다.
                사용자가 제출한 로그를 바탕으로 **근본 원인(Root Cause)**을 찾아내야 합니다.

                [분석 지침]
                1. 단순한 로그 번역을 하지 마세요. 로그가 **왜** 발생했는지 추론하세요.
                2. 하드웨어 결함(H/W), 소프트웨어 버그(S/W), 설정 오류(Config), 물리적 이슈(Cable/SFP) 중 어디에 해당하는지 판단하세요.
                3. 해결책은 막연한 가이드가 아니라, **당장 장비에 입력해야 할 구체적인 명령어(CLI)**를 포함해야 합니다.

                [입력 로그]
                {log_input[:30000]}

                [출력 형식] (마크다운 사용)

                ### 1. 🎯 근본 원인 (Root Cause)
                * **진단:** (예: 모듈 1번의 ASIC 칩셋 통신 불량 / OSPF Neighbor MTU 불일치 등 구체적으로)
                * **설명:** 이 로그가 발생하게 된 기술적 배경을 설명하세요.

                ### 2. 📉 영향도 분석 (Impact)
                * **현재 상태:** (예: 해당 인터페이스 통신 단절, 장비 전체 리부팅 위험 등)
                * **잠재 위험:** 조치하지 않을 경우 발생할 수 있는 추가 장애.

                ### 3. 🛠️ 해결 및 검증 방법 (Action Plan)
                * **Step 1 (긴급 조치):** 당장 수행해야 할 작업.
                * **Step 2 (검증 명령어):** 원인을 확진하기 위해 입력해볼 CLI 명령어.
                  (예: `show platform`, `show interface transceiver detail` 등)
                * **Step 3 (TAC 케이스):** 하드웨어 교체(RMA)가 필요한지 여부 판단.
                """
                
                result = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.markdown(result, unsafe_allow_html=True) # 여기도 HTML 허용

# ========================================================
# [TAB 2] 스펙 조회기 (수정됨: <br> 태그 문제 해결)
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
                # [핵심 수정] unsafe_allow_html=True를 추가하여 <br> 태그가 줄바꿈으로 보이게 함
                st.markdown(get_gemini_response(prompt, API_KEY_SPEC, 'spec'), unsafe_allow_html=True)

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
                    family_prompt = "당신은 Cisco Nexus(NX-OS) 전문가입니다. 반드시 **NX-OS 버전**만 추천하세요. IOS-XE 버전을 추천하면 절대 안 됩니다."
                    search_keyword = "Nexus"
                else:
                    family_prompt = "당신은 Cisco Catalyst(IOS-XE) 전문가입니다. 반드시 **IOS-XE 버전**만 추천하세요. NX-OS 버전을 추천하면 절대 안 됩니다."
                    search_keyword = "Catalyst"

                current_ver_query = f"Cisco {search_keyword} {os_model} {os_ver if os_ver else ''} Last Date of Support"
                current_ver_url = f"https://www.google.com/search?q={current_ver_query.replace(' ', '+')}"

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
                
                st.markdown(get_gemini_response(prompt, API_KEY_OS, 'os'), unsafe_allow_html=True)
