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
    st.stop()

# ========================================================
# 💾 [수정됨] 서버 메모리를 활용한 영구 카운터
# ========================================================
# @st.cache_resource를 쓰면 새로고침해도 데이터가 날아가지 않습니다.
@st.cache_resource
def get_shared_usage_stats():
    # 이 함수는 서버가 켜져있는 동안 딱 한 번만 실행되어 저장소를 만듭니다.
    return {
        'date': str(datetime.date.today()),
        'stats': {
            "log_lite": 0, "log_flash": 0, "log_pro": 0,
            "spec_lite": 0, "spec_flash": 0, "spec_pro": 0,
            "os_lite": 0, "os_flash": 0, "os_pro": 0,
            "class_lite": 0, "class_flash": 0, "class_pro": 0 # 분류 기능 추가
        }
    }

# 공유 데이터 가져오기
shared_data = get_shared_usage_stats()
today_str = str(datetime.date.today())

# 날짜가 바뀌었으면 리셋
if shared_data['date'] != today_str:
    shared_data['date'] = today_str
    for key in shared_data['stats']:
        shared_data['stats'][key] = 0

# ========================================================
# 🤖 사이드바 설정 (계층형 디자인)
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    
    # 1. 모델 선택
    selected_model_name = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
        ("Gemini 2.5 Flash Lite (가성비)", "Gemini 2.5 Flash (표준)", "Gemini 3 Flash Preview (최신)")
    )
    
    # 2. 모델 매핑
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

    # 3. 사용량 현황판 (스타일 적용)
    st.markdown("### 📊 일일 누적 사용량")
    st.caption(f"📅 {today_str} 기준 (새로고침 해도 유지됨)")

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

    draw_usage("🚨 로그 분류 (Classify)", "class")
    draw_usage("📊 로그 분석 (Log Key)", "log")
    draw_usage("🔍 스펙 조회 (Spec Key)", "spec")
    draw_usage("💿 OS 추천 (OS Key)", "os")

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
        
        # [수정됨] 공유 데이터 카운트 증가
        count_key = f"{func_prefix}_{current_model_type}"
        shared_data['stats'][count_key] += 1
        
        return response.text
    except Exception as e:
        return f"System Error: {str(e)}"

# ========================================================
# 🖥️ 메인 화면 구성
# ========================================================
st.title("🛡️ Cisco Technical AI Dashboard")

# [NEW] 탭 순서 변경: 로그 분류가 맨 앞으로
tab0, tab1, tab2, tab3 = st.tabs(["🚨 로그 분류 (New)", "📊 로그 정밀 분석", "🔍 하드웨어 스펙", "💿 OS 추천"])

# ========================================================
# [TAB 0] 로그 분류기 (신규 기능)
# ========================================================
with tab0:
    st.header("⚡ 대량 로그 자동 분류")
    st.caption("복잡한 로그를 붙여넣으면 심각도(Critical/Warning/Info) 별로 분류해 드립니다.")
    
    raw_log_input = st.text_area("분류할 전체 로그를 입력하세요:", height=200, key="raw_log_area")
    
    if st.button("로그 분류 실행", key="btn_classify"):
        if not raw_log_input:
            st.warning("로그를 입력해주세요!")
        else:
            with st.spinner("로그 패턴 분석 및 심각도 분류 중..."):
                prompt = f"""
                당신은 시스코 로그 분석 전문가입니다. 
                아래 로그들을 분석하여 심각도(Critical, Warning, Info) 별로 분류하고 요약해주세요.
                
                [입력 로그]
                {raw_log_input}

                [출력 형식]
                각 로그 그룹에 대해 다음과 같이 출력하세요. (마크다운 형식)
                
                ### 🔴 Critical (심각한 장애)
                - (로그 내용 요약)
                - (로그 원본 일부)
                
                ### 🟡 Warning (경고)
                - (로그 내용 요약)
                
                ### 🔵 Info (일반 정보)
                - (로그 내용 요약)

                마지막에 **[분석 제안]** 섹션을 만들어서 정밀 분석이 필요한 핵심 로그만 따로 추출해 주세요.
                """
                # 로그 키(API_KEY_LOG)를 공유해서 사용
                classified_result = get_gemini_response(prompt, API_KEY_LOG, 'class')
                st.session_state['classified_result'] = classified_result # 결과 저장
                
    # 분류 결과가 있으면 보여주기
    if 'classified_result' in st.session_state:
        st.markdown("---")
        st.subheader("📋 분류 결과")
        st.markdown(st.session_state['classified_result'])
        
        st.info("💡 위 결과 중 정밀 분석하고 싶은 로그를 복사하여 '📊 로그 정밀 분석' 탭에서 분석하세요.")
        
        # (기능 추가) 버튼을 누르면 분석 탭 입력창으로 값 넘겨주기
        if st.button("📝 원본 로그를 '로그 정밀 분석' 탭으로 복사하기"):
             st.session_state['log_transfer'] = raw_log_input
             st.success("복사되었습니다! 상단의 '📊 로그 정밀 분석' 탭을 눌러 이동하세요.")

# ========================================================
# [TAB 1] 로그 분석기 (연동 기능 추가)
# ========================================================
with tab1:
    st.header("로그 분석 및 장애 진단")
    
    # 탭0에서 넘어온 데이터가 있으면 그걸 기본값으로 사용
    default_log_value = st.session_state.get('log_transfer', "")
    
    log_input = st.text_area("분석할 로그를 입력하세요:", value=default_log_value, height=150, key="log_analysis_area")
    
    if st.button("로그 분석 실행", key="btn_log"):
        if not log_input: st.warning("로그를 입력해주세요!")
        else:
            with st.spinner(f"AI가 로그를 분석 중입니다..."):
                prompt = f"""
                당신은 시스코 전문가입니다. 다음 로그를 분석하되, 반드시 아래 형식대로 답변하세요.
                로그: {log_input}
                답변 형식:
                [PART_1](발생 원인)
                [PART_2](네트워크 영향)
                [PART_3](조치 방법)
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
    with col1: os_model = st.text_input("장비 모델명", placeholder="예: C9300-48P or N9K-C93180YC-FX", key="os_model")
    with col2: os_ver = st.text_input("현재 버전 (선택)", placeholder="예: 17.09.04a or 10.2(3)", key="os_ver")
        
    if st.button("OS 분석 실행", key="btn_os"):
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
                
                response_html = get_gemini_response(prompt, API_KEY_OS, 'os')
                st.markdown(response_html, unsafe_allow_html=True)

# 날짜가 바뀌었거나 데이터가 없으면 리셋
if 'usage_stats' not in st.session_state or st.session_state.usage_stats.get('date') != today_str:
    st.session_state.usage_stats = {'date': today_str}
    for key in usage_keys:
        st.session_state.usage_stats[key] = 0

# ========================================================
# 🤖 사이드바 설정 (계층형 디자인)
# ========================================================
with st.sidebar:
    st.header("🤖 엔진 설정")
    
    # 1. 모델 선택
    selected_model_name = st.selectbox(
        "사용할 AI 모델을 선택하세요:",
        ("Gemini 2.5 Flash Lite (가성비)", "Gemini 2.5 Flash (표준)", "Gemini 3 Flash Preview (최신)")
    )
    
    # 2. 모델 매핑
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

    # 3. 사용량 현황판 (스타일 적용)
    st.markdown("### 📊 일일 사용량 현황")
    st.caption(f"📅 {today_str} 기준 (자정 리셋)")

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
        lite = st.session_state.usage_stats[f"{prefix}_lite"]
        flash = st.session_state.usage_stats[f"{prefix}_flash"]
        pro = st.session_state.usage_stats[f"{prefix}_pro"]
        
        st.markdown(f"""
        <div class="usage-box">
            <div class="usage-title">{title}</div>
            <div class="usage-item"><span>🔹 Lite (2.5)</span> <span class="usage-num">{lite}회</span></div>
            <div class="usage-item"><span>⚡ Flash (2.5)</span> <span class="usage-num">{flash}회</span></div>
            <div class="usage-item"><span>🚀 Pro (3.0)</span> <span class="usage-num">{pro}회</span></div>
        </div>
        """, unsafe_allow_html=True)

    draw_usage("📊 로그 분석 (Log Key)", "log")
    draw_usage("🔍 스펙 조회 (Spec Key)", "spec")
    draw_usage("💿 OS 추천 (OS Key)", "os")

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
        
        # 카운트 증가
        count_key = f"{func_prefix}_{current_model_type}"
        st.session_state.usage_stats[count_key] += 1
        
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
            with st.spinner(f"AI가 로그를 분석 중입니다..."):
                prompt = f"""
                당신은 시스코 전문가입니다. 다음 로그를 분석하되, 반드시 아래 형식대로 답변하세요.
                로그: {log_input}
                답변 형식:
                [PART_1](발생 원인)
                [PART_2](네트워크 영향)
                [PART_3](조치 방법)
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
                st.markdown(get_gemini_response(prompt, API_KEY_SPEC, 'spec'))

# [TAB 3] OS 추천기 (수정됨: 장비 계열 선택 추가)
with tab3:
    st.header("OS 추천 및 안정성 진단")
    st.caption("💡 장비 계열을 먼저 선택하면 더 정확한 추천을 받을 수 있습니다.")

    # [NEW] 장비 계열 선택 (Radio Button)
    device_family = st.radio(
        "장비 계열 선택 (Device Family)",
        ("Catalyst (IOS-XE)", "Nexus (NX-OS)"),
        horizontal=True
    )
    
    col1, col2 = st.columns(2)
    with col1: os_model = st.text_input("장비 모델명", placeholder="예: C9300-48P or N9K-C93180YC-FX", key="os_model")
    with col2: os_ver = st.text_input("현재 버전 (선택)", placeholder="예: 17.09.04a or 10.2(3)", key="os_ver")
        
    if st.button("OS 분석 실행", key="btn_os"):
        if not os_model: st.warning("장비 모델명은 필수입니다!")
        else:
            with st.spinner(f"{device_family} 데이터베이스 검색 중..."):
                
                # 프롬프트 제약 조건 설정 (선택에 따라 달라짐)
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
                1. **마크다운(Markdown)을 쓰지 마세요.** 오직 `<table>`, `<tr>`, `<td>` 태그만 사용하세요.
                2. 모든 링크(URL)는 반드시 `<a href='URL' target='_blank' style='color:#007bff; text-decoration:none; font-weight:bold;'>🔍 EOL 확인</a>` 형식을 사용하여 **새 창에서 열리도록** 하세요.
                3. 테이블 스타일: `<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>`
                4. 헤더 스타일: `<th style='background-color:#f0f2f6; padding:8px;'>`
                5. 셀 스타일: `<td style='padding:8px;'>`

                [분석 내용]
                - MD(Maintenance Deployment) 및 Gold Star 버전을 최우선 추천.
                - 안정성 등급은 별점(⭐⭐⭐⭐⭐)으로 표시.
                - 'Last Date of Support'는 예측값을 기입.

                [대상 장비]: {os_model} ({device_family} 계열)
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
                      <td>(버전)</td>
                      <td>⭐⭐⭐⭐⭐</td>
                      <td>(날짜)</td>
                      <td>안정성 우수</td>
                      <td><a href='https://www.google.com/search?q=Cisco+{os_model}+EOL' target='_blank'>🔍 EOL 확인</a></td>
                   </tr>
                </table>
                """
                
                response_html = get_gemini_response(prompt, API_KEY_OS, 'os')
                st.markdown(response_html, unsafe_allow_html=True)

