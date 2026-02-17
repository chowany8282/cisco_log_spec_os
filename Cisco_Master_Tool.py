import streamlit as st
import google.generativeai as genai
import datetime
from collections import Counter
import re

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
@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {
        "log_lite": 0, "log_flash": 0, "log_pro": 0,
        "spec_lite": 0, "spec_flash": 0, "spec_pro": 0,
        "os_lite": 0, "os_flash": 0, "os_pro": 0
    }}

shared_data = get_shared_usage_stats()

if shared_data['date'] != str(datetime.date.today()):
    shared_data['date'] = str(datetime.date.today())
    for k in shared_data['stats']: shared_data['stats'][k] = 0

# 입력창 지우기 함수들
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
    
    st.markdown("---")
    st.subheader("📊 API 사용량 통계")
    st.caption(f"📅 {shared_data['date']} 기준")

    stats = shared_data['stats']
    st.markdown("""
    <style>
    .stat-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        font-size: 13px;
    }
    .stat-row { display: flex; justify-content: space-between; }
    .stat-val { font-weight: bold; color: #0068c9; }
    </style>
    """, unsafe_allow_html=True)

    def draw_stat(title, prefix):
        lite = stats[f"{prefix}_lite"]
        flash = stats[f"{prefix}_flash"]
        pro = stats[f"{prefix}_pro"]
        st.markdown(f"""
        <div class="stat-box">
            <strong>{title}</strong>
            <div class="stat-row">Lite: <span class="stat-val">{lite}</span></div>
            <div class="stat-row">Flash: <span class="stat-val">{flash}</span></div>
            <div class="stat-row">Pro: <span class="stat-val">{pro}</span></div>
        </div>
        """, unsafe_allow_html=True)

    draw_stat("🚨 정밀 분석 (RCA)", "log")
    draw_stat("🔍 스펙 조회", "spec")
    draw_stat("💿 OS 추천", "os")
    st.caption("* '로그 분류' 탭은 AI를 쓰지 않아 카운트되지 않습니다.")

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

tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 통합 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류
# ========================================================
with tab0:
    st.header("⚡ 장애 로그 필터링 (복사 가능)")
    st.caption("정상 로그(Up/Down 포함)는 제외하고, 조치가 필요한 로그만 보여줍니다.")
    
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택 (.txt, .log)", type=['txt', 'log'])
        raw_log_input = st.text_area("📝 또는 로그 붙여넣기:", height=200, key="raw_log_area")
        submitted = st.form_submit_button("🚀 분석 실행")

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
            issue_counter = Counter()
            lines = final_log.splitlines()
            
            ignore_keywords = [
                "transceiver absent", "administratively down", "mgmt0", 
                "default policer", "removed", "inserted", "vty", 
                "last reset", "connection timed out", "changed state to up",
                "link-keepalive", "dummy range", "online", "ready", 
                "recovery", "recovered", "neighbor up", "copy complete",
                "changed state to down", "link-3-updown", "lineproto-5-updown"
            ]
            
            issue_keywords = [
                "-0-", "-1-", "-2-", "-3-", "-4-", 
                "traceback", "crash", "reload", "stuck", "panic", 
                "error", "warning", "threshold", "exceeded", "buffer", 
                "tahusd", "fail", "collision", "duplex mismatch", 
                "authentication failed"
            ]
            
            for line in lines:
                line_strip = line.strip()
                if not line_strip: continue
                line_lower = line_strip.lower() 
                
                if any(x in line_lower for x in ignore_keywords): continue 

                if "%" in line_strip:
                    msg_start = line_strip.find("%")
                    clean_msg = line_strip[msg_start:]
                else:
                    clean_msg = line_strip

                if any(k in clean_msg.lower() for k in issue_keywords):
                    issue_counter[clean_msg] += 1
            
            total_issues = sum(issue_counter.values())
            
            if total_issues > 0:
                st.markdown(f"### 🚨 총 {total_issues}건의 이슈 발견 (Click to Copy)")
                st.markdown("> 각 로그 우측 상단의 **📄 아이콘**을 누르면 복사됩니다.")
                
                for log_msg, count in issue_counter.most_common():
                    display_text = f"{log_msg} (x {count}건)" if count > 1 else log_msg
                    st.code(display_text, language="text")
                    
                file_lines = []
                for log_msg, count in issue_counter.most_common():
                    file_lines.append(f"{log_msg} (x {count}건)" if count > 1 else log_msg)
                
                final_report_text = "\n".join(file_lines)

            else:
                st.success("✅ 필터링 결과, 특이사항(장애)이 없습니다.")
                st.info("참고: Interface Up/Down 및 단순 알림 로그는 제외되었습니다.")
                final_report_text = "No critical issues found."

            st.session_state['res_class'] = final_report_text
            st.session_state['log_buf'] = final_log
            
        else:
            st.warning("로그를 입력하세요.")

    if 'res_class' in st.session_state and st.session_state['res_class'] != "No critical issues found.":
        st.download_button(
            label="📥 결과 리포트 저장 (txt)",
            data=st.session_state['res_class'],
            file_name="Filtered_Issue_Report.txt",
            mime="text/plain",
            key="down_0"
        )
        
        # [수정된 복사 버튼 로직]
        if st.button("📝 정밀 분석 탭으로 복사"):
            source_log = st.session_state.get('log_buf', "")
            # 1. 전달할 데이터 저장
            st.session_state['log_transfer'] = source_log
            # 2. [핵심] 다음 탭의 입력창 위젯(Key)에 강제로 값 주입
            st.session_state['log_analysis_area'] = source_log
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 정밀 분석 (수정: Session State 연동)
# ========================================================
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    
    # [수정] 위젯 키(log_analysis_area)가 없으면 초기화
    if 'log_analysis_area' not in st.session_state:
        st.session_state['log_analysis_area'] = st.session_state.get('log_transfer', "")

    # text_area의 값을 session_state와 key로 직접 연동
    log_in = st.text_area(
        "로그 입력:", 
        height=200, 
        key="log_analysis_area"  # 이 키를 통해 Tab0에서 값을 주입받음
    )
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🚀 분석 실행"):
            if log_in:
                with st.spinner("Gemini AI가 정밀 분석 중..."):
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
# [TAB 2] 스펙 조회
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
# [TAB 3] OS 추천
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
