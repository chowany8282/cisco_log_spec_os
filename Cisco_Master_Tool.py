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
    st.error("🚨 API 키를 찾을 수 없습니다. secrets.toml을 확인하세요.")
    st.stop()

# ========================================================
# 💾 사용량 카운터
# ========================================================
usage_keys = ["log_lite", "log_flash", "log_pro", "spec_lite", "spec_flash", "spec_pro", "os_lite", "os_flash", "os_pro"]

@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {k: 0 for k in usage_keys}}

shared_data = get_shared_usage_stats()

# 입력창 초기화 함수
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
        response = model.generate_content(prompt)
        shared_data['stats'][f"{prefix}_{m_type}"] += 1
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ========================================================
# 🖥️ 메인 화면
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류 (Logic)", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류 (순수 Python 로직 - AI 미사용)
# ========================================================
with tab0:
    st.header("⚡ 로그 정밀 분류 (Rule-Based)")
    st.caption("AI를 쓰지 않고, 시스코 표준 심각도(Severity) 규칙에 따라 기계적으로 분류합니다.")
    
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (.txt, .log)", type=['txt', 'log'])
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
                st.success(f"파일 로드 성공 ({len(final_log)} Bytes)")
            except Exception as e:
                st.error(f"오류: {e}")
        elif raw_log_input:
            final_log = raw_log_input

        if final_log:
            # ------------------------------------------------
            # [순수 로직] Python으로 한 줄씩 검사
            # ------------------------------------------------
            critical_logs = []
            warning_logs = []
            info_logs = []
            
            lines = final_log.split('\n')
            
            for line in lines:
                line_str = line.strip()
                if not line_str: continue
                line_lower = line_str.lower() # 소문자로 변환해서 검사
                
                # [0] 예외 처리: 심각해 보이지만 실제로는 별거 아닌 것들 (Info로 강제 이동)
                # SFP 제거(Transceiver Absent), Admin Down, 관리포트(mgmt0), CoPP, VTY 설정 등
                if any(x in line_lower for x in ["transceiver absent", "administratively down", "mgmt0", "default policer", "removed", "inserted", "vty", "last reset"]):
                    info_logs.append(line_str)
                    continue # 다음 줄로 넘어감

                # [1] Critical (심각도 0, 1, 2) + 치명적 키워드
                # %FACILITY-0-..., -1-, -2- 패턴 찾기
                if any(x in line_lower for x in ["-0-", "-1-", "-2-", "traceback", "crash", "reload", "stuck", "panic"]):
                    critical_logs.append(line_str)
                
                # [2] Warning (심각도 3, 4) + 경고 키워드
                # %FACILITY-3-..., -4- 패턴 찾기 (Buffer Exceeded는 보통 -4- 임)
                elif any(x in line_lower for x in ["-3-", "-4-", "error", "warning", "threshold", "exceeded", "buffer", "tahusd", "fail"]):
                    warning_logs.append(line_str)
                        
                # [3] Info (심각도 5, 6, 7) + 나머지
                else:
                    info_logs.append(line_str)

            # ------------------------------------------------
            # [결과 출력 생성]
            # ------------------------------------------------
            result_text = f"### 📊 분석 결과 (총 {len(lines)}줄)\n"
            result_text += "> **분류 기준:** 시스코 심각도 Level 0~2(Critical), 3~4(Warning), 5~7(Info)\n\n"
            
            # 1. Critical
            result_text += f"#### 🔴 Critical ({len(critical_logs)}건)\n"
            if critical_logs:
                for l in critical_logs: result_text += f"- `{l}`\n"
            else:
                result_text += "- ✅ 발견되지 않음\n"
                
            # 2. Warning
            result_text += f"\n#### 🟡 Warning ({len(warning_logs)}건)\n"
            if warning_logs:
                for l in warning_logs: result_text += f"- `{l}`\n"
            else:
                result_text += "- ✅ 발견되지 않음\n"
            
            # 3. Info (너무 많으면 100개까지만 표시하고 생략)
            result_text += f"\n#### 🔵 Info / Others ({len(info_logs)}건)\n"
            if info_logs:
                count = 0
                for l in info_logs:
                    if count < 100: # 100줄까지만 보여줌 (속도 위해)
                        result_text += f"- `{l}`\n"
                    count += 1
                if count > 100:
                    result_text += f"\n... (총 {count}건 중 나머지 {count-100}건은 생략됨)"
            else:
                result_text += "- ✅ 발견되지 않음\n"

            # 결과 저장
            st.session_state['res_class'] = result_text
            st.session_state['log_buf'] = final_log
            
        else:
            st.warning("로그를 입력하세요.")

    # 결과 표시 및 다운로드
    if 'res_class' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state['res_class'])
        
        st.download_button(
            label="📥 결과 텍스트로 저장",
            data=st.session_state['res_class'],
            file_name="Log_Classification_Result.txt",
            mime="text/plain",
            key="down_0"
        )
        
        if st.button("📝 정밀 분석 탭으로 복사"):
            st.session_state['log_transfer'] = st.session_state.get('log_buf', "")
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 정밀 분석 (여기는 AI 유지)
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
                    Cisco Tier 3 엔지니어 관점에서 로그 분석:
                    1. 🎯 근본 원인 (Root Cause)
                    2. 📉 영향도 (Impact)
                    3. 🛠️ 해결 방법 (CLI 명령어 포함)
                    
                    [로그] {log_in[:50000]}
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
# [TAB 2] 스펙 조회 (AI 유지)
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
# [TAB 3] OS 추천 (AI 유지)
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
