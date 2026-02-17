import streamlit as st
import google.generativeai as genai
import datetime

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
except:
    st.error("🚨 API 키를 찾을 수 없습니다.")
    st.stop()

# ========================================================
# 💾 사용량 카운터 설정
# ========================================================
usage_keys = ["log_lite", "log_flash", "log_pro", "spec_lite", "spec_flash", "spec_pro", "os_lite", "os_flash", "os_pro"]

@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {k: 0 for k in usage_keys}}

shared_data = get_shared_usage_stats()

# ========================================================
# 🧹 입력창 초기화 함수들
# ========================================================
def clear_log_input(): st.session_state["raw_log_area"] = ""
def clear_analysis_input(): st.session_state["log_analysis_area"] = ""
def clear_spec_input(): st.session_state["input_spec"] = ""
def clear_os_input(): st.session_state["os_model"] = ""; st.session_state["os_ver"] = ""

# ========================================================
# 🤖 사이드바 설정
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    model_opt = st.selectbox("AI 모델:", ("Gemini 2.5 Flash Lite", "Gemini 2.5 Flash", "Gemini 3 Flash Preview"))
    
    if "Lite" in model_opt: MODEL_ID, m_type = "models/gemini-2.5-flash-lite", "lite"
    elif "Preview" in model_opt: MODEL_ID, m_type = "models/gemini-3-flash-preview", "pro"
    else: MODEL_ID, m_type = "models/gemini-2.5-flash", "flash"
    
    st.success(f"선택: {model_opt}")

# AI 호출 함수
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
# 🖥️ 메인 화면
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류 (분류 성능 대폭 강화)
# ========================================================
with tab0:
    st.header("⚡ 로그 자동 분류")
    
    # 1. 파일 제한 및 폼 설정
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (.txt, .log 만 가능)", type=['txt', 'log'])
        raw_log_input = st.text_area("📝 또는 로그 붙여넣기:", height=200, key="raw_log_area")
        submitted = st.form_submit_button("🚀 분류 실행")

    st.button("🗑️ 지우기", on_click=clear_log_input, key="clr_0")

    if submitted:
        final_log = ""
        if uploaded_file:
            try:
                bytes_data = uploaded_file.getvalue()
                try: final_log = bytes_data.decode("utf-8")
                except: final_log = bytes_data.decode("cp949", errors="ignore")
                st.success(f"파일 로드 성공: {uploaded_file.name}")
            except Exception as e:
                st.error(f"오류: {e}")
        elif raw_log_input:
            final_log = raw_log_input

        if final_log:
            with st.spinner("로그 패턴 정밀 분석 중... (잡다한 로그 제거 중)"):
                # [🔥 핵심 수정] 프롬프트를 아주 구체적으로 변경하여 분류 정확도 향상
                prompt = f"""
                당신은 Cisco 본사의 **Senior TAC 엔지니어**입니다.
                제공된 로그 파일에서 **장애 원인 분석에 필요한 핵심 로그**만 추출하여 분류하세요.
                
                [🚨 분류 기준 (Strict Rules)]
                1. **Critical (즉시 조치 필요):** - 장비 Crash, 재부팅(Reload), 모듈 Fail, Power Fail, Fan Fail.
                   - OSPF/BGP/EIGRP Neighbor Down (단, 의도적 종료 제외).
                   - Interface Link Down (단, 'Admin down'이나 'Transceiver Absent'는 제외).
                   - 온도 경보(Over Temperature).

                2. **Warning (점검 필요):** - CPU/Memory High Usage (임계치 초과).
                   - Smart License 관련 인증 실패/만료.
                   - SFP 트랜시버 호환성 경고 (Unqualified/Not Supported).
                   - Port-Security Violation (포트 보안 위반).
                   - Duplex Mismatch.

                3. **Info (주요 변경 사항):** - Config 변경 내역(Configure terminal).
                   - 사용자 로그인/로그아웃.
                   - (주의: 단순한 Up/Down 반복이나 상태 조회 로그는 과감히 생략하세요.)

                [출력 형식]
                전체 로그를 다 보여주지 말고, **같은 유형의 로그는 하나로 묶어서** 요약하세요.
                
                ### 🔴 Critical
                **1. 모듈 2번 장애 발생 (Module Failed)**
                - **발생 횟수:** 1회
                - **설명:** 모듈 2번이 응답하지 않아 시스템에서 격리되었습니다.
                ```
                %MODULE-2-FAILED: Module 2 failed
                ```

                ### 🟡 Warning
                **1. 스마트 라이선스 인증 실패**
                - **발생 횟수:** 다수
                - **설명:** 라이선스 서버와 통신이 되지 않아 인증이 실패했습니다.
                ```
                %SMART_LIC-3-AUTHORIZATION_FAILED: ...
                ```

                [입력 로그 데이터]
                {final_log[:50000]} 
                """
                # (로그가 너무 길면 잘릴 수 있어서 5만 자로 제한)

                res = get_gemini_response(prompt, API_KEY_LOG, 'log')
                
                st.session_state['res_class'] = res
                st.session_state['log_buf'] = final_log
        else:
            st.warning("파일을 선택하거나 내용을 입력하세요.")

    # 결과 화면 및 다운로드
    if 'res_class' in st.session_state:
        st.markdown("---")
        st.subheader("🎯 분석 제안")
        st.markdown(st.session_state['res_class'], unsafe_allow_html=True)
        
        st.download_button(
            label="📥 결과 텍스트로 저장",
            data=st.session_state['res_class'],
            file_name="Log_Classification.txt",
            mime="text/plain",
            key="down_0"
        )
        
        if st.button("📝 정밀 분석 탭으로 복사"):
            st.session_state['log_transfer'] = st.session_state.get('log_buf', "")
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 정밀 분석 (다운로드 고침)
# ========================================================
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    val = st.session_state.get('log_transfer', "")
    log_in = st.text_area("로그 입력:", value=val, height=200, key="log_analysis_area")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🚀 분석 실행"):
            if log_in:
                with st.spinner("분석 중..."):
                    prompt = f"""
                    Cisco Tier 3 엔지니어 관점에서 근본 원인(Root Cause)과 해결책(CLI)을 제시하세요.
                    **한글**로 답변하고, 다음 항목을 포함하세요:
                    1. 근본 원인 (Root Cause)
                    2. 서비스 영향도 (Impact)
                    3. 조치 방법 (Action Plan - 구체적 명령어 포함)
                    
                    [로그] {log_in[:30000]}
                    """
                    res = get_gemini_response(prompt, API_KEY_LOG, 'log')
                    st.session_state['res_anal'] = res
            else:
                st.warning("로그를 입력하세요.")
    with col2:
        st.button("🗑️ 지우기", on_click=clear_analysis_input, key="clr_1")

    if 'res_anal' in st.session_state:
        st.markdown(st.session_state['res_anal'], unsafe_allow_html=True)
        st.download_button(
            label="📥 결과 텍스트로 저장",
            data=st.session_state['res_anal'],
            file_name="Root_Cause_Analysis.txt",
            mime="text/plain",
            key="down_1"
        )

# ========================================================
# [TAB 2] 스펙 조회 (다운로드 고침)
# ========================================================
with tab2:
    st.header("스펙 조회")
    m_in = st.text_input("모델명 (예: C9300)", key="input_spec")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("조회 실행"):
            if m_in:
                with st.spinner("검색 중..."):
                    res = get_gemini_response(f"{m_in} 하드웨어 스펙 표로 정리", API_KEY_SPEC, 'spec')
                    st.session_state['res_spec'] = res
            else:
                st.warning("모델명을 입력하세요.")
    with col2:
        st.button("🗑️ 지우기", on_click=clear_spec_input, key="clr_2")

    if 'res_spec' in st.session_state:
        st.markdown(st.session_state['res_spec'], unsafe_allow_html=True)
        st.download_button(
            label="📥 결과 텍스트로 저장",
            data=st.session_state['res_spec'],
            file_name="Hardware_Spec.txt",
            mime="text/plain",
            key="down_2"
        )

# ========================================================
# [TAB 3] OS 추천 (다운로드 고침)
# ========================================================
with tab3:
    st.header("OS 추천")
    fam = st.radio("계열:", ("Catalyst", "Nexus"), horizontal=True)
    os_mod = st.text_input("모델명", key="os_model")
    os_ver = st.text_input("현재 버전", key="os_ver")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("추천 실행"):
            if os_mod:
                with st.spinner("검색 중..."):
                    prompt = f"{fam} 장비 {os_mod} 추천 OS (MD/Gold Star) 테이블로 출력\n현재 버전: {os_ver}"
                    res = get_gemini_response(prompt, API_KEY_OS, 'os')
                    st.session_state['res_os'] = res
            else:
                st.warning("모델명을 입력하세요.")
    with col2:
        st.button("🗑️ 지우기", on_click=clear_os_input, key="clr_3")

    if 'res_os' in st.session_state:
        st.markdown(st.session_state['res_os'], unsafe_allow_html=True)
        st.download_button(
            label="📥 결과 텍스트로 저장",
            data=st.session_state['res_os'],
            file_name="OS_Recommendation.txt",
            mime="text/plain",
            key="down_3"
        )
