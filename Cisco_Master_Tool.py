import streamlit as st
import google.generativeai as genai
import datetime
from collections import Counter

# ========================================================
# 🎨 페이지 설정
# ========================================================
st.set_page_config(page_title="Cisco AI Master System", page_icon="🛡️", layout="wide")

# ========================================================
# 🔑 API 키 설정
# ========================================================
try:
    API_KEY_LOG = st.secrets["API_KEY_LOG"]
    API_KEY_SPEC = st.secrets["API_KEY_SPEC"]
    API_KEY_OS = st.secrets["API_KEY_OS"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다. secrets.toml을 확인하세요.")
    st.stop()

# ========================================================
# 💾 상태 관리
# ========================================================
@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {
        "log_lite": 0, "log_flash": 0, "log_pro": 0,
        "spec_lite": 0, "spec_flash": 0, "spec_pro": 0,
        "os_lite": 0, "os_flash": 0, "os_pro": 0
    }}

shared_data = get_shared_usage_stats()

def clear_tab1(): st.session_state["log_analysis_area"] = ""
def clear_tab2(): st.session_state["input_spec"] = ""
def clear_tab3(): st.session_state["os_model"] = ""; st.session_state["os_ver"] = ""

# ========================================================
# 🤖 사이드바
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    model_opt = st.selectbox("AI 모델 선택:", ("Gemini 2.5 Flash", "Gemini 3 Flash Preview", "Gemini 2.5 Flash Lite"))
    
    if "Lite" in model_opt: MODEL_ID, m_type = "models/gemini-2.5-flash-lite", "lite"
    elif "Preview" in model_opt: MODEL_ID, m_type = "models/gemini-3-flash-preview", "pro"
    else: MODEL_ID, m_type = "models/gemini-2.5-flash", "flash"
    
    st.markdown("---")
    st.subheader("📊 API 사용량")
    stats = shared_data['stats']
    for title, prefix in [("🚨 분석", "log"), ("🔍 스펙", "spec"), ("💿 OS", "os")]:
        st.write(f"**{title}**: {stats[f'{prefix}_{m_type}']}회")

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
tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 통합 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# --------------------------------------------------------
# [TAB 0] 로그 분류 (버그 수정: "group" 단어 오인식 해결)
# --------------------------------------------------------
with tab0:
    st.header("⚡ 최신 1000줄 정밀 분석 (Bug Fix)")
    st.caption("파일의 **맨 마지막 1000줄**만 분석합니다. (Pool-group 등의 단어가 필터링되는 오류 수정됨)")
    
    with st.form("tab0_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("📂 로그 파일 선택", type=['txt', 'log'], key="uploader_tab0")
        raw_input = st.text_area("📝 또는 직접 붙여넣기:", height=200, key="raw_log_area")
        submitted = st.form_submit_button("🚀 분석 실행")

    if submitted:
        content = ""
        if uploaded_file:
            content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        elif raw_input:
            content = raw_input
            
        if content:
            # 1. 라인 분리 및 1000줄 자르기
            all_lines = content.splitlines()
            total_len = len(all_lines)
            
            if total_len > 1000:
                target_lines = all_lines[-1000:]
                msg_info = f"총 {total_len}줄 중 **최신 1000줄**만 분석했습니다."
            else:
                target_lines = all_lines
                msg_info = f"총 {total_len}줄 전체를 분석했습니다. (1000줄 미만)"

            issue_counter = Counter()
            
            # [수정됨] 이슈 키워드
            issue_keywords = ["-0-", "-1-", "-2-", "-3-", "-4-", "traceback", "crash", "threshold", "exceeded", "buffer", "fail", "down", "error", "collision", "mismatch", "tahusd"]
            
            # [핵심 수정] "up" 단어 삭제 -> 구체적인 문장으로 변경
            # 이제 "Pool-group"이 "up" 때문에 사라지지 않습니다.
            ignore_keywords = [
                "mgmt0", "absent", "admin down", "vty", 
                "changed state to up", "is up", "link-3-updown", # "up" 대신 구체적 명시
                "recovery", "recovered", "online", "ready", "inserted", "removed",
                "authentication success", "copy complete", "link-keepalive"
            ]
            
            for line in target_lines:
                line_lower = line.lower()
                
                # 이슈 키워드는 있고, 무시 키워드는 없는지 확인
                if any(k in line_lower for k in issue_keywords) and not any(i in line_lower for i in ignore_keywords):
                    # 타임스탬프 제거 후 메시지만 추출
                    msg = line[line.find("%"):] if "%" in line else line.strip()
                    issue_counter[msg] += 1
            
            res_text = "\n".join([f"{m} (x {c}건)" if c > 1 else m for m, c in issue_counter.most_common()])
            st.session_state['res_class'] = res_text
            
            st.success(msg_info)
            
            if issue_counter:
                st.markdown(f"### 🚨 발견된 이슈: 총 {sum(issue_counter.values())}건")
                for m, c in issue_counter.most_common():
                    st.code(f"{m} (x {c}건)" if c > 1 else m, language="text")
            else:
                st.info("선택된 구간(최신 1000줄) 내에서 특이사항이 발견되지 않았습니다.")

    # 결과 처리 버튼들
    if st.session_state.get('res_class'):
        st.download_button("📥 분류 결과 저장", data=st.session_state['res_class'], file_name="Recent_Issues.txt", key="dl_tab0")
        
        if st.button("📝 분류된 이슈만 정밀 분석으로 복사", key="copy_btn"):
            st.session_state['log_analysis_area'] = st.session_state['res_class']
            st.success("복사 완료! '📊 정밀 분석' 탭으로 이동하세요.")

# --------------------------------------------------------
# [TAB 1] 정밀 분석 (RCA)
# --------------------------------------------------------
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    if 'log_analysis_area' not in st.session_state:
        st.session_state['log_analysis_area'] = ""

    log_in = st.text_area("분석할 로그를 입력하세요:", height=300, key="log_analysis_area")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🚀 분석 실행", key="btn_tab1"):
            if log_in:
                with st.spinner("AI 분석 중..."):
                    res = get_gemini_response(f"Cisco 엔지니어 관점에서 원인/영향/조치 분석: {log_in[:30000]}", API_KEY_LOG, "log")
                    st.session_state['res_anal'] = res
            else: st.warning("로그를 입력하세요.")
    with col2:
        if st.button("🗑️ 지우기", key="clr_tab1"):
            st.session_state["log_analysis_area"] = ""
            st.rerun()

    if st.session_state.get('res_anal'):
        st.markdown(st.session_state['res_anal'], unsafe_allow_html=True)

# --------------------------------------------------------
# [TAB 2] 스펙 조회
# --------------------------------------------------------
with tab2:
    st.header("🔍 하드웨어 스펙 조회")
    spec_in = st.text_input("모델명 입력 (예: C9300):", key="input_spec")
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🚀 스펙 조회", key="btn_tab2"):
            if spec_in:
                with st.spinner("데이터 찾는 중..."):
                    res = get_gemini_response(f"Cisco {spec_in} 하드웨어 스펙 요약 표", API_KEY_SPEC, "spec")
                    st.markdown(res, unsafe_allow_html=True)
    with col2:
        if st.button("🗑️ 지우기", key="clr_tab2"):
            st.session_state["input_spec"] = ""
            st.rerun()

# --------------------------------------------------------
# [TAB 3] OS 추천
# --------------------------------------------------------
with tab3:
    st.header("💿 OS 버전 추천")
    os_m = st.text_input("장비 모델명:", key="os_model")
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🚀 추천 버전 조회", key="btn_tab3"):
            if os_m:
                with st.spinner("권장 버전 분석 중..."):
                    res = get_gemini_response(f"{os_m} 장비 추천 OS 표 형식", API_KEY_OS, "os")
                    st.markdown(res, unsafe_allow_html=True)
    with col2:
        if st.button("🗑️ 지우기", key="clr_tab3"):
            st.session_state["os_model"] = ""
            st.rerun()
