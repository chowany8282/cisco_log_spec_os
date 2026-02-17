import streamlit as st
import google.generativeai as genai
import datetime
import os

# ========================================================
# 🎨 페이지 기본 설정 (무조건 가장 첫 줄!)
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
    st.info("배포 시: Streamlit Cloud 설정의 'Secrets' 메뉴에 키를 입력하세요.")
    st.stop()

# ========================================================
# ⏳ 사용량 카운터 초기화 (세션 상태 관리)
# ========================================================
# 1. 오늘 날짜 확인
today_str = datetime.date.today().isoformat()

# 2. 세션 상태에 '사용량 데이터'가 없거나, 날짜가 바뀌었으면 리셋
if 'usage_data' not in st.session_state or st.session_state.usage_data['date'] != today_str:
    st.session_state.usage_data = {
        'date': today_str,
        'Gemini 2.5 Flash Lite': 0,
        'Gemini 2.5 Flash': 0,
        'Gemini 3 Flash Preview': 0
    }

# ========================================================
# 🤖 사이드바 설정 (카운터 표시)
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    
    # 모델 ID 매핑 정보
    model_map = {
        "Gemini 2.5 Flash Lite": "models/gemini-2.5-flash-lite",
        "Gemini 2.5 Flash": "models/gemini-2.5-flash",
        "Gemini 3 Flash Preview": "models/gemini-3-flash-preview"
    }

    # 선택지 문구 만들기 (예: "모델명 (오늘 사용: 5회)")
    selection_options = []
    for model_name in model_map.keys():
        count = st.session_state.usage_data.get(model_name, 0)
        selection_options.append(f"{model_name} (오늘 사용: {count}회)")

    # 셀렉트박스 표시
    selected_option_str = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
        selection_options
    )

    # 선택된 문구에서 '진짜 모델 이름'만 추출하기
    # 예: "Gemini 2.5 Flash (오늘 사용: 5회)" -> "Gemini 2.5 Flash"
    current_model_name = selected_option_str.split(" (오늘 사용:")[0]
    MODEL_ID = model_map[current_model_name]

    st.success(f"현재 엔진: {MODEL_ID}")
    st.info(f"📅 기준 날짜: {today_str}")
    st.markdown("---")
    st.markdown("Created by Wan Hee Cho")

# ========================================================
# 🤖 AI 연결 함수 (카운트 증가 로직 추가)
# ========================================================
def get_gemini_response(prompt, current_api_key, model_friendly_name):
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(prompt)
        
        # [중요] 성공적으로 응답을 받으면 카운트 +1
        st.session_state.usage_data[model_friendly_name] += 1
        
        return response.text
    except Exception as e:
        return f"System Error: {str(e)}"

# ========================================================
# 🖥️ 메인 화면 구성
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")
st.markdown("네트워크 엔지니어를 위한 **로그 분석, 스펙 조회, OS 추천** 올인원 솔루션입니다.")

tab1, tab2, tab3 = st.tabs(["📊 로그 정밀 분석", "🔍 하드웨어 스펙 조회", "💿 OS 추천"])

# [TAB 1] 로그 분석기
with tab1:
    st.header("로그 분석 및 장애 진단")
    log_input = st.text_area("분석할 로그를 입력하세요:", height=150)
    if st.button("로그 분석 실행", key="btn_log"):
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"AI가 로그를 분석 중입니다... ({current_model_name})"):
                prompt = f"""
                당신은 시스코 전문가입니다. 다음 로그를 분석하되, 반드시 아래 형식대로 답변하세요.
                로그: {log_input}
                답변 형식:
                [PART_1](발생 원인)
                [PART_2](네트워크 영향)
                [PART_3](조치 방법)
                """
                # 함수 호출 시 current_model_name을 같이 넘겨서 카운트 증가시킴
                result = get_gemini_response(prompt, API_KEY_LOG, current_model_name)
                try:
                    p1 = result.split("[PART_1]")[1].split("[PART_2]")[0].strip()
                    p2 = result.split("[PART_2]")[1].split("[PART_3]")[0].strip()
                    p3 = result.split("[PART_3]")[1].strip()
                    st.subheader("🔴 발생 원인"); st.error(p1)
                    st.subheader("🟡 네트워크 영향"); st.warning(p2)
                    st.subheader("🟢 권장 조치"); st.success(p3)
                except: st.markdown(result)

# [TAB 2] 스펙 조회기
with tab2:
    st.header("장비 하드웨어 스펙 조회")
    model_input = st.text_input("장비 모델명 (예: C9300-48P)", key="input_spec")
    if st.button("스펙 조회 실행", key="btn_spec"):
        if not model_input: st.warning("모델명을 입력해주세요!")
        else:
            with st.spinner("데이터시트 검색 중..."):
                prompt = f"""
                [대상 모델]: {model_input}
                위 모델의 하드웨어 스펙을 표(Table)로 요약해주세요.
                항목: Fixed Ports, Switching Capacity, Forwarding Rate, CPU/Memory, Power.
                주요 특징 3가지 포함. 한국어 답변.
                """
                st.markdown(get_gemini_response(prompt, API_KEY_SPEC, current_model_name))

# [TAB 3] OS 추천기
with tab3:
    st.header("OS 추천 및 안정성 진단")
    st.caption("💡 추천 OS와 안정성 등급을 확인하고, **우측 링크를 클릭하여 EOL 날짜를 검증**하세요.")
    
    col1, col2 = st.columns(2)
    with col1: os_model = st.text_input("장비 모델명", placeholder="예: Nexus 93180YC-FX", key="os_model")
    with col2: os_ver = st.text_input("현재 버전 (선택)", placeholder="예: 17.06.01", key="os_ver")
        
    if st.button("OS 분석 실행", key="btn_os"):
        if not os_model: st.warning("장비 모델명은 필수입니다!")
        else:
            with st.spinner("안정성(Stability) 데이터 분석 및 HTML 리포트 생성 중..."):
                
                current_ver_query = f"Cisco {os_model} {os_ver if os_ver else ''} Last Date of Support"
                current_ver_url = f"https://www.google.com/search?q={current_ver_query.replace(' ', '+')}"

                prompt = f"""
                당신은 시스코 TAC 엔지니어입니다.
                다음 장비의 **OS 소프트웨어**를 분석하여 **HTML Table** 코드로 출력하세요.

                [필수 지침]
                1. **마크다운(Markdown)을 쓰지 마세요.** 오직 `<table>`, `<tr>`, `<td>` 태그만 사용하세요.
                2. 모든 링크(URL)는 반드시 `<a href='URL' target='_blank' style='color:#007bff; text-decoration:none; font-weight:bold;'>🔍 EOL 확인</a>` 형식을 사용하여 **새 창에서 열리도록** 하세요.
                3. 테이블 스타일: `<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>`
                4. 헤더 스타일: `<th style='background-color:#f0f2f6; padding:8px;'>`
                5. 셀 스타일: `<td style='padding:8px;'>`

                [분석 내용]
                - MD(Maintenance Deployment) 및 Gold Star 버전을 최우선 추천.
                - 안정성 등급은 별점(⭐⭐⭐⭐⭐)으로 표시.
                - 'Last Date of Support'는 예측값을 기입.

                [대상 장비]: {os_model}
                [현재 OS 버전]: {os_ver if os_ver else '정보 없음'}
                [현재 버전 검증 링크]: {current_ver_url}

                출력할 내용은 오직 HTML 코드뿐이어야 합니다. (```html ... ``` 코드 블록 없이 순수 HTML만 출력)
                
                <h3>1. 현재 버전 상태</h3>
                <table>...</table>
                <br>
                <h3>2. 추천 OS (Recommended Releases)</h3>
                <table>
                   <tr>
                      <th>순위</th> <th>버전명</th> <th>안정성 등급</th> <th>EOL(예측)</th> <th>추천 사유</th> <th>검증 링크</th>
                   </tr>
                   <tr>
                      <td>🥇 1순위</td>
                      <td>17.9.5</td>
                      <td>⭐⭐⭐⭐⭐</td>
                      <td>2027-10-31</td>
                      <td>안정성 우수</td>
                      <td><a href='https://www.google.com/search?q=Cisco+{os_model}+17.9.5+Last+Date+of+Support' target='_blank'>🔍 EOL 확인</a></td>
                   </tr>
                </table>
                """
                
                response_html = get_gemini_response(prompt, API_KEY_OS, current_model_name)
                st.markdown(response_html, unsafe_allow_html=True)
