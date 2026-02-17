import streamlit as st
import google.generativeai as genai
import datetime
from collections import Counter

# 🎨 페이지 설정
st.set_page_config(page_title="Cisco AI Master System", page_icon="🛡️", layout="wide")

# 🔑 API 키 설정
try:
    API_KEY_LOG = st.secrets["API_KEY_LOG"]
    API_KEY_SPEC = st.secrets["API_KEY_SPEC"]
    API_KEY_OS = st.secrets["API_KEY_OS"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다.")
    st.stop()

# 💾 사용량 카운터 복구
@st.cache_resource
def get_shared_usage_stats():
    return {'date': str(datetime.date.today()), 'stats': {
        "log_lite": 0, "log_flash": 0, "log_pro": 0,
        "spec_lite": 0, "spec_flash": 0, "spec_pro": 0,
        "os_lite": 0, "os_flash": 0, "os_pro": 0
    }}
shared_data = get_shared_usage_stats()

# 🤖 사이드바 통계 UI
with st.sidebar:
    st.header("🤖 엔진 설정")
    model_opt = st.selectbox("AI 모델:", ("Gemini 2.5 Flash", "Gemini 3 Flash Preview", "Gemini 2.5 Flash Lite"))
    MODEL_ID = "models/gemini-2.5-flash" if "2.5 Flash" in model_opt else "models/gemini-3-flash-preview"
    m_type = "flash" if "2.5 Flash" in model_opt else "pro"
    
    st.markdown("---")
    st.subheader("📊 API 사용량 통계")
    for title, prefix in [("🚨 정밀 분석", "log"), ("🔍 스펙 조회", "spec"), ("💿 OS 추천", "os")]:
        st.write(f"**{title}** (Total: {sum([shared_data['stats'][f'{prefix}_{t}'] for t in ['lite', 'flash', 'pro']])})")

def get_gemini_response(prompt, key, prefix):
    genai.configure(api_key=key)
    model = genai.GenerativeModel(MODEL_ID)
    res = model.generate_content(prompt)
    shared_data['stats'][f"{prefix}_{m_type}"] += 1
    return res.text

st.title("🛡️ Cisco Technical AI Dashboard")
tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 통합 분류", "📊 정밀 분석", "🔍 스펙 조회", "💿 OS 추천"])

# [TAB 0] 로그 분류
with tab0:
    st.header("⚡ 장애 로그 필터링")
    uploaded_file = st.file_uploader("📂 로그 파일 선택", type=['txt', 'log'])
    if st.button("🚀 분석 실행") or uploaded_file:
        if uploaded_file:
            content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            lines = content.splitlines()
            issue_counter = Counter()
            # 필터링 로직 (단순화)
            issue_keywords = ["-0-", "-1-", "-2-", "-3-", "-4-", "traceback", "crash", "threshold", "exceeded", "buffer", "fail"]
            for line in lines:
                if any(k in line.lower() for k in issue_keywords) and not any(i in line.lower() for i in ["mgmt0", "absent"]):
                    msg = line[line.find("%"):] if "%" in line else line
                    issue_counter[msg] += 1
            
            res_text = "\n".join([f"{m} (x {c}건)" if c > 1 else m for m, c in issue_counter.most_common()])
            st.session_state['res_class'] = res_text
            st.session_state['log_buf'] = content # 원문 보관
            
            st.markdown(f"### 🚨 총 {sum(issue_counter.values())}건의 이슈 발견")
            for m, c in issue_counter.most_common():
                st.code(f"{m} (x {c}건)" if c > 1 else m, language="text")

    if st.session_state.get('res_class'):
        # ✨ 여기가 핵심 수정 포인트!
        if st.button("📝 분류된 로그만 정밀 분석 탭으로 복사"):
            target_text = st.session_state['res_class']
            st.session_state['log_transfer'] = target_text
            st.session_state['log_analysis_area'] = target_text
            st.success("분류된 이슈 리스트만 복사되었습니다!")

# [TAB 1] 정밀 분석
with tab1:
    st.header("🕵️‍♀️ 심층 분석 (RCA)")
    log_in = st.text_area("로그 입력:", value=st.session_state.get('log_analysis_area', ""), height=300, key="log_analysis_area")
    if st.button("🚀 분석 실행"):
        st.write(get_gemini_response(f"엔지니어 관점 분석: {log_in[:30000]}", API_KEY_LOG, "log"))
