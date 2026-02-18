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
    st.error("🚨 API 키를 찾을 수 없습니다. secrets.toml 파일을 확인해주세요.")
    st.stop()

# ========================================================
# 💾 사용량 카운터 설정
# ========================================================
usage_keys = ["select_cnt", "log_cnt", "spec_cnt", "os_cnt"]

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
            "Gemini 2.5 Lite (초고속/가성비)",
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
    select_c = shared_data['stats']['select_cnt']
    log_c = shared_data['stats']['log_cnt']
    spec_c = shared_data['stats']['spec_cnt']
    os_c = shared_data['stats']['os_cnt']

    st.text(f"⚡ 로그분석: {select_c}회")
    st.text(f"📊 정밀진단: {log_c}회")
    st.text(f"🔍 스펙조회: {spec_c}회")
    st.text(f"💿 OS 추천:  {os_c}회")

    st.markdown("---")
    st.markdown("Created by Wan Hee Cho")

# ========================================================
# 🤖 AI 연결 및 에러 처리 함수
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
        if "429" in error_msg or "Quota" in error_msg:
            return f"""
            ### ⛔ **일일 무료 사용량 초과 (Quota Exceeded)**
            오늘 할당된 무료 사용량을 모두 소진했습니다.
            **💡 해결 방법:** 사이드바에서 모델을 **'Gemini 2.5 Lite'**로 변경해 보세요.
            """
        elif "404" in error_msg or "Not Found" in error_msg:
            return f"""
            ### ❌ **모델 미지원 (Model Not Found)**
            현재 계정에서 `{MODEL_ID}` 모델을 사용할 수 없습니다.
            **💡 해결 방법:** 사이드바에서 **'Gemini 2.5 Flash'**를 선택해 주세요.
            """
        else:
            return f"### 🚨 시스템 에러 발생\n\n```\n{error_msg}\n```"

# ========================================================
# 🖥️ 메인 화면 구성
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["📑 로그 요약 분석", "📊 로그 정밀 진단", "🔍 하드웨어 스펙", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 요약 분석기 (수정됨: 2가지 항목만 출력 + 코드블록 강제)
# ========================================================
with tab0:
    st.header("📑 로그 핵심 요약 (Summary & Attention)")
    st.caption("로그 파일을 분석하여 **전체 요약**과 **주의가 필요한 로그**만 추출합니다.")
    
    uploaded_file = st.file_uploader("📂 로그 파일 업로드 (txt, log)", type=["txt", "log"])
    raw_log_input = st.text_area("📝 또는 여기에 로그를 직접 붙여넣으세요:", height=200, key="raw_log_area")
    
    col_btn1, col_btn2 = st.columns([1, 6])
    with col_btn1:
        run_btn = st.button("분석 실행", key="btn_classify")
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
            st.warning("분석할 로그를 입력해주세요!")
        else:
            with st.spinner(f"🤖 AI({MODEL_ID.split('/')[-1]})가 핵심 내용만 요약 중입니다..."):
                # [수정된 프롬프트] 1번, 3번만 출력하고 로그는 코드블록으로 감싸기
                prompt = f"""
                당신은 Cisco 네트워크 엔지니어입니다.
                아래 로그 파일을 분석하여 **딱 두 가지 항목**으로만 요약하세요.

                [출력 형식 가이드]
                1. **전체 요약 (Executive Summary):**
                   - 로그의 전반적인 상태(정상/장애/작업 등)를 3~5줄로 명확히 요약하세요.
                
                2. **주요 주의 사항 (Attention Required):**
                   - Error, Warning, Fail, Traceback 등 엔지니어가 확인해야 할 로그만 추출하세요.
                   - **[중요]** 특정 로그 메시지를 인용할 때는 반드시 **코드 블록(```)**으로 감싸서 출력하세요. (사용자가 복사하기 쉽게)
                   - 예시: 
                     * 인터페이스 에러 발생: 
                     ```
                     %LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down
                     ```

                [제외 대상]
                - 타임라인, 운영 맥락, 결론 등은 모두 생략하세요.
                - 의미 없는 반복 로그는 하나로 합치세요.

                [입력 데이터]
                {final_log_content}
                """
                classified_result = get_gemini_response(prompt, API_KEY_LOG, 'select')
                st.session_state['classified_result'] = classified_result 
                
    if 'classified_result' in st.session_state:
        st.markdown("---")
        
        # 전체 복사 버튼
        col_copy_btn, col_copy_msg = st.columns([2, 5])
        with col_copy_btn:
            if st.button("📝 분석 결과 전체 복사"):
                 st.session_state['log_transfer'] = st.session_state['classified_result']
                 st.success("✅ 복사 완료! '심층 장애 진단' 탭에서 사용할 수 있습니다.")
        
        st.subheader("🎯 핵심 분석 결과")
        st.markdown(st.session_state['classified_result'])

# ========================================================
# [TAB 1] 심층 장애 진단
# ========================================================
with tab1:
    st.header("📊 로그 정밀 진단 & 솔루션")
    default_log_value = st.session_state.get('log_transfer', "")
    log_input = st.text_area("분석할 로그(또는 위에서 복사한 내용)를 입력하세요:", value=default_log_value, height=150, key="log_analysis_area")
    
    c1, c2 = st.columns([1, 6])
    with c1:
        btn_run_log = st.button("심층 분석 실행", key="btn_log")
    with c2:
        st.button("🗑️ 입력창 지우기", on_click=clear_analysis_input, key="clr_anal")

    if btn_run_log:
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"AI가 심층 진단 중입니다..."):
                prompt = f"""
                당신은 시스코 전문가입니다. 
                아래 로그 내용을 정밀 분석하여 다음 형식으로 답하세요.
                
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
                except: 
                    st.markdown(result)

# ========================================================
# [TAB 2] 스펙 조회기
# ========================================================
with tab2:
    st.header("🔍 장비 하드웨어 스펙 조회")
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
    st.header("💿 OS 추천 및 안정성 진단")
    
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
            with st.spinner(f"추천 버전을 검색 중..."):
                if "Nexus" in device_family:
                    family_prompt = "당신은 Cisco Nexus(NX-OS) 전문가입니다. 반드시 **NX-OS 버전**만 추천하세요."
                else:
                    family_prompt = "당신은 Cisco Catalyst(IOS-XE) 전문가입니다. 반드시 **IOS-XE 버전**만 추천하세요."

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

                <h3>1. 현재 버전 상태</h3>
                <table>...</table>
                <br>
                <h3>2. 추천 OS (Recommended Releases)</h3>
                <table>...</table>
                """
                
                response_html = get_gemini_response(prompt, API_KEY_OS, 'os')
                response_html = response_html.replace("```html", "").replace("```", "")
                
                st.markdown(response_html, unsafe_allow_html=True)

