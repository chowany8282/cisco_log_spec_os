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
# 💾 사용량 카운터 (복구 및 유지)
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

def clear_log_input(): st.session_state["raw_log_area"] = ""
def clear_analysis_input(): st.session_state["log_analysis_area"] = ""
def clear_spec_input(): st.session_state["input_spec"] = ""
def clear_os_input(): st.session_state["os_model"] = ""; st.session_state["os_ver"] = ""

# ========================================================
# 🤖 사이드바 설정 (통계 UI)
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
    stats = shared_data['stats']
    st.markdown("""
    <style>
    .stat-box { background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; font-size: 13px; }
    .stat-row { display: flex; justify-content: space-between; }
    .stat-val { font-weight: bold; color: #0068c9; }
    </style>
    """, unsafe_allow_html=True)

    def draw_stat(title, prefix):
        lite, flash, pro = stats[f"{prefix}_lite"], stats[f"{prefix}_flash"], stats[f"{prefix}_pro"]
        st.markdown(f'<div class="stat-box"><strong>{title}</strong>'
                    f'<div class="stat-row">Lite: <span class="stat-val">{lite}</span></div>'
                    f'<div class="stat-row">Flash: <span class="stat-val">{flash}</span></div>'
                    f'<div class="stat-row">Pro: <span class="stat-val">{pro}</span></div></div>', unsafe_allow_html=True)

    draw_stat("🚨 정밀 분석 (RCA)", "log")
    draw_stat("🔍 스펙 조회", "spec")
    draw_stat("💿 OS 추천", "os")

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
# [TAB 0] 로그 분류 (순수 로직 모드 - 필터 조정)
# ========================================================
with tab0:
    st.header("⚡ 장애 로그 필터링 (Logic Mode)")
    st.caption("AI 없이 시스코 로그 심각도 규칙으로 분류합니다. (인터페이스 Down 로그 포함)")
    
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
                st.success(f"파일 로드 성공")
            except Exception as e:
                st.error(f"오류: {e}")
        elif raw_log_input:
            final_log = raw_log_input

        if final_log:
            issue_counter = Counter()
            lines = final_log.splitlines()
            
            # [수정] 필터링 목록을 "진짜 필요 없는 것" 위주로 축소
            ignore_keywords = [
                "transceiver absent", "mgmt0", "default policer", 
                "removed", "inserted", "vty", "last reset", 
                "connection timed out", "changed state to up",
                "link-keepalive", "dummy range", "online", "ready", 
                "recovery", "recovered", "neighbor up", "copy complete"
            ]
            
            # [수정] 이슈 키워드 (인터페이스 Down 다시 포함)
            issue_keywords = [
                "-0-", "-1-", "-2-", "-3-", "-4-", 
                "traceback", "crash", "reload", "stuck", "panic", 
                "error", "warning", "threshold", "exceeded", "buffer", 
                "tahusd", "fail", "collision", "duplex mismatch", 
                "down", "authentication failed" 
            ]
            
            for line in lines:
                line_strip = line.strip()
                if not line_strip: continue
                line_lower = line_strip.lower() 
                
                # 무시 목록 체크
                if any(x in line_lower for x in ignore_keywords): continue 

                # 타임스탬프 제거 및 메시지 추출
                if "%" in line_strip:
                    msg_start = line_strip.find("%")
                    clean_msg = line_strip[msg_start:]
                else:
                    clean_msg = line_strip

                # 이슈 키워드 포함 시 카운팅
                if any(k in clean_msg.lower() for k in issue_keywords):
                    issue_counter[clean_msg] += 1
            
            total_issues = sum(issue_counter.values())
            
            if total_issues > 0:
                st.markdown(f"### 🚨 총 {total_issues}건의 이슈 발견 (Click to Copy)")
                for log_msg, count in issue_counter.most_common():
                    display_text = f"{log_msg} (x {count}건)" if count > 1 else log_msg
                    st.code(display_text, language="text") # 클릭 복사 기능
                
                # 세션 저장용
                file_lines = [f"{m} (x {c}건)" if c > 1 else m for m, c in issue_counter.most_common()]
                st.session_state['res_class'] = "\n".join(file_lines)
                st.session_state['log_buf'] = final_log
            else:
                st.success("✅ 특이사항이 없습니다.")
                st.session_state['res_class'] = "No issues found."
        else:
            st.warning("로그를 입력하세요.")

    if 'res_class' in st.session_state and st.session_state['res_class'] != "No issues found.":
        st.download_button("📥 리포트 저장", data=st.session_state['res_class'], file_name="Log_Report.txt")
        if st.button("📝 정밀 분석 탭으로 복사"):
            st.session_state['log_transfer'] = st.session_state.get('log_buf', "")
            st.session_state['log_analysis_area'] = st.session_state.get('log_buf', "")
            st.success("복사 완료! 옆 탭으로 이동하세요.")

# ========================================================
# [TAB 1] 정밀 분석 (AI)
# ========================================================
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    if 'log_analysis_area' not in st.session_state:
        st.session_state['log_analysis_area'] = st.session_state.get('log_transfer', "")

    log_in = st.text_area("로그 입력:", height=200, key="log_analysis_area")
    
    if st.button("🚀 분석 실행"):
        if log_in:
            with st.spinner("Gemini AI 분석 중..."):
                prompt = f"Cisco Tier 3 엔지니어 관점에서 원인/영향/해결책(CLI) 제시:\n[로그]\n{log_in[:50000]}"
                res = get_gemini_response(prompt, API_KEY_LOG, 'log')
                st.session_state['res_anal'] = res
        else: st.warning("로그를 입력하세요.")

    if 'res_anal' in st.session_state:
        st.markdown(st.session_state['res_anal'], unsafe_allow_html=True)
        st.download_button("📥 결과 저장", data=st.session_state['res_anal'], file_name="RCA_Result.txt")

# [TAB 2], [TAB 3]는 이전과 동일한 로직 유지 (생략하지만 코드엔 포함되어야 함)
# (지면상 생략하지만 실제 코드에선 이전 답변의 TAB2, TAB3 코드를 그대로 붙여넣으시면 됩니다.)
