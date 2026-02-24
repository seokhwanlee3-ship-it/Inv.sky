import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
import plotly.express as px
from dart_handler import DartHandler
import datetime
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DART 금융 대시보드",
    page_icon="📈",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 데이터 로딩 및 처리 함수 (Function Definitions)
# -----------------------------------------------------------------------------
# 함수 정의를 사이드바 로직보다 먼저 배치해야 실행 오류(NameError)가 발생하지 않음

@st.cache_resource
def get_dart_handler(key):
    return DartHandler(key)

@st.cache_data
def load_all_financials(_handler, corp_code, start_year, end_year):
    data_list = []
    quarters = ['11013', '11012', '11014', '11011'] # 1Q, 2Q, 3Q, 4Q
    
    progress_bar = st.progress(0)
    total_steps = (end_year - start_year + 1) * 4
    step = 0

    for year in range(start_year, end_year + 1):
        for reprt_code in quarters:
            # UI용 진행률 업데이트
            step += 1
            progress_bar.progress(step / total_steps)

            data = _handler.get_financial_data(corp_code, year, reprt_code)
            if data:
                q_map = {'11013': 1, '11012': 2, '11014': 3, '11011': 4}
                quarter_num = q_map[reprt_code]
                
                data_list.append({
                    'Year': year,
                    'Quarter': quarter_num,
                    'Revenue_Acc': data['revenue'].iloc[0] if isinstance(data['revenue'], pd.Series) else data['revenue'],
                    'OpIncome_Acc': data['op_income'].iloc[0] if isinstance(data['op_income'], pd.Series) else data['op_income'],
                    'NetIncome_Acc': data['net_income'].iloc[0] if isinstance(data['net_income'], pd.Series) else data['net_income'],
                    'Period': f"{year}.{quarter_num}Q"
                })
    
    progress_bar.empty()
    return pd.DataFrame(data_list)

def process_quarterly_data(df):
    if df.empty: return df
    
    df = df.sort_values(by=['Year', 'Quarter'])
    df['Revenue'] = 0.0
    df['OpIncome'] = 0.0
    df['NetIncome'] = 0.0

    years = df['Year'].unique()
    for year in years:
        year_data = df[df['Year'] == year]
        
        # 1Q
        q1 = year_data[year_data['Quarter'] == 1]
        if not q1.empty:
            idx = q1.index[0]
            df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc']
            df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc']
            df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc']

        # 2Q ~ 4Q (누적 차감)
        for q in [2, 3, 4]:
            curr = year_data[year_data['Quarter'] == q]
            prev = year_data[year_data['Quarter'] == (q - 1)]
            
            if not curr.empty:
                idx = curr.index[0]
                if not prev.empty:
                    df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc'] - prev.iloc[0]['Revenue_Acc']
                    df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc'] - prev.iloc[0]['OpIncome_Acc']
                    df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc'] - prev.iloc[0]['NetIncome_Acc']
                else:
                    # 이전 분기 데이터가 없으면 누적값 사용
                    df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc']
                    df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc']
                    df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc']
    
    return df

# -----------------------------------------------------------------------------
# 3. 사이드바 (설정)
# -----------------------------------------------------------------------------
st.sidebar.title("설정 (Settings)")

# API Key 로드
load_dotenv()
api_key_input = os.getenv("DART_API_KEY")

if api_key_input:
    st.sidebar.success("API Key 로드됨 (.env)")
else:
    st.sidebar.error("API Key를 찾을 수 없습니다. .env 파일을 확인해주세요.")
    st.stop()

# 종목 검색
corp_name = st.sidebar.text_input("종목명 검색", value="지아이이노베이션")

# 분석 기간
current_year = datetime.datetime.now().year
years = st.sidebar.slider("분석 기간 (Year)", 2020, current_year, (current_year-3, current_year))

# -----------------------------------------------------------------------------
# 4. 네비게이션 (Sidebar Navigation)
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
nav_menu = st.sidebar.radio(
    "메뉴 선택",
    ["🏠 피드 (Feed)", "📝 내메모 (My Note)", "📢 공시 (Disclosures)", "📡 IR", "📊 증권사리포트", "📰 뉴스"]
)

# -----------------------------------------------------------------------------
# 5. 메인 UI 로직
# -----------------------------------------------------------------------------

try:
    handler = get_dart_handler(api_key_input)
    corp_code = handler.find_corp_code(corp_name)
    
    if not corp_code:
        st.error(f"'{corp_name}'을(를) 찾을 수 없습니다.")
        st.stop()

    # 상장 종목코드(Stock Code) 찾기
    stock_code = None
    try:
        corp_list = handler.dart.corp_codes
        row = corp_list[corp_list['corp_name'] == corp_name]
        if not row.empty:
            stock_code = row.iloc[0]['stock_code']
    except:
        pass

    # 헤더
    st.title(f"{corp_name} ({stock_code if stock_code else corp_code})")

    # 메뉴별 콘텐츠 렌더링
    if nav_menu == "🏠 피드 (Feed)":
        # -------------------------------------------------------------------------
        # Chart Section (FinanceDataReader)
        # -------------------------------------------------------------------------
        if stock_code:
            st.subheader("주가 추이 (Stock Price)")
            
            # 상단 컨트롤 (주기 + 이동평균선)
            col_ctrl1, col_ctrl2 = st.columns([1, 2])
            with col_ctrl1:
                chart_freq = st.radio(
                    "차트 주기",
                    ["일봉 (Day)", "주봉 (Week)", "월봉 (Month)", "년봉 (Year)"],
                    horizontal=True
                )
            with col_ctrl2:
                selected_mas = st.multiselect(
                    "이동평균선 선택",
                    [3, 5, 10, 20, 60, 120, 200],
                    default=[5, 20, 60]
                )
            
            start_date = f"{years[0]}-01-01"
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            df_stock = fdr.DataReader(stock_code, start_date, end_date)
            
            if not df_stock.empty:
                # 데이터 리샘플링
                if chart_freq == "주봉 (Week)":
                    df_resampled = df_stock.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                elif chart_freq == "월봉 (Month)":
                    df_resampled = df_stock.resample('M').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                elif chart_freq == "년봉 (Year)":
                    df_resampled = df_stock.resample('Y').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                else:
                    df_resampled = df_stock

                # 차트 생성
                fig_stock = go.Figure()
                
                # 캔들스틱 추가 (색상: 상승 빨강, 하락 연한 파랑)
                fig_stock.add_trace(go.Candlestick(
                    x=df_resampled.index,
                    open=df_resampled['Open'],
                    high=df_resampled['High'],
                    low=df_resampled['Low'],
                    close=df_resampled['Close'],
                    name='Price',
                    increasing_line_color='red', increasing_fillcolor='red',
                    decreasing_line_color='deepskyblue', decreasing_fillcolor='deepskyblue'
                ))
                
                # 이동평균선 계산 및 추가
                ma_colors = {3: 'orange', 5: 'gold', 10: 'magenta', 20: 'green', 60: 'cyan', 120: 'purple', 200: 'black'}
                for ma in selected_mas:
                    df_resampled[f'MA{ma}'] = df_resampled['Close'].rolling(window=ma).mean()
                    fig_stock.add_trace(go.Scatter(
                        x=df_resampled.index,
                        y=df_resampled[f'MA{ma}'],
                        mode='lines',
                        name=f'{ma}선',
                        line=dict(width=1.5, color=ma_colors.get(ma, 'grey'))
                    ))

                fig_stock.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_stock, use_container_width=True)
            else:
                st.info("주가 데이터를 가져올 수 없습니다.")
        else:
            st.info("비상장 기업이거나 종목코드를 찾을 수 없어 주가 차트를 표시하지 않습니다.")

        # -------------------------------------------------------------------------
        # Financial Analysis Section
        # -------------------------------------------------------------------------
        st.subheader("재무 성과 (Financial Performance)")
        
        with st.spinner("DART에서 재무 데이터를 수집 중입니다..."):
            df_raw = load_all_financials(handler, corp_code, years[0], years[1])
            df_quarterly = process_quarterly_data(df_raw)

        if not df_quarterly.empty:
            # 가장 최신 데이터 표시
            latest = df_quarterly.iloc[-1]
            last_period = latest['Period']
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            
            def format_billions(val):
                return f"{val/100000000:.1f} 억"

            # 0으로 나누기 방지
            rev = latest['Revenue']
            opm = (latest['OpIncome']/rev*100) if rev else 0
            npm = (latest['NetIncome']/rev*100) if rev else 0

            col1.metric("매출액 (Revenue)", format_billions(latest['Revenue']), f"{last_period} 기준")
            col2.metric("영업이익 (Op. Income)", format_billions(latest['OpIncome']), f"이익률 {opm:.1f}%")
            col3.metric("순이익 (Net Income)", format_billions(latest['NetIncome']), f"이익률 {npm:.1f}%")

            # -------------------------------------------------------------------------
            # Visualization
            # -------------------------------------------------------------------------
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            
            # 1. 비용 구조 (Pie Chart)
            with col_chart1:
                st.markdown("#### 비용 구조 (Cost Structure)")
                cost = latest['Revenue'] - latest['OpIncome']
                cost_data = pd.DataFrame({
                    'Category': ['영업비용 (Cost)', '영업이익 (Profit)'],
                    'Value': [cost, latest['OpIncome']]
                })
                fig_pie = px.pie(cost_data, values='Value', names='Category', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)

            # 2. 이익률 추이 (Bar + Line Combo)
            with col_chart2:
                st.markdown("#### 영업이익률 추이 (OPM Trend)")
                # 0으로 나누기 방지
                df_quarterly['OPM'] = df_quarterly.apply(lambda x: (x['OpIncome']/x['Revenue']*100) if x['Revenue'] else 0, axis=1)
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=df_quarterly['Period'], y=df_quarterly['OpIncome'], name='영업이익', marker_color='#4e79a7'))
                
                # 보조축
                fig_bar.add_trace(go.Scatter(x=df_quarterly['Period'], y=df_quarterly['OPM'], name='이익률(%)', yaxis='y2', mode='lines+markers', line=dict(color='#e15759', width=2)))
                
                fig_bar.update_layout(
                    yaxis=dict(title="금액 (원)"),
                    yaxis2=dict(title="이익률 (%)", overlaying='y', side='right'),
                    legend=dict(x=0.01, y=0.99),
                    height=400
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with st.expander("📑 상세 재무제표 보기 (Detailed Financials)"):
                st.dataframe(df_quarterly.style.format({
                    'Revenue': '{:,.0f}',
                    'OpIncome': '{:,.0f}',
                    'NetIncome': '{:,.0f}',
                    'Revenue_Acc': '{:,.0f}'
                }), use_container_width=True)
        else:
             st.warning("기간 내 공시된 재무 데이터가 없습니다.")

    elif nav_menu == "📝 내메모 (My Note)":
        st.subheader("📝 투자 메모")
        if 'notes' not in st.session_state:
            st.session_state.notes = ""
        user_note = st.text_area("해당 종목에 대한 분석 내용을 기록하세요.", value=st.session_state.notes, height=300)
        if st.button("메모 저장"):
            st.session_state.notes = user_note
            st.success("메모가 저장되었습니다.")

    elif nav_menu == "📢 공시 (Disclosures)":
        st.subheader(f"📢 {corp_name} 최근 공시 목록")
        with st.spinner("공시 목록을 불러오는 중입니다..."):
             mj_disclosures = handler.get_recent_disclosures(corp_code, count=50)
             if mj_disclosures is not None and not mj_disclosures.empty:
                 display_cols = ['rcept_dt', 'corp_cls', 'report_nm', 'flr_nm']
                 exist_cols = [c for c in display_cols if c in mj_disclosures.columns]
                 df_disp = mj_disclosures[exist_cols].copy()
                 if 'rcept_dt' in df_disp.columns:
                    df_disp['rcept_dt'] = df_disp['rcept_dt'].astype(str).apply(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}" if len(x)==8 else x)
                 df_disp.rename(columns={'rcept_dt': '접수일자', 'corp_cls': '법인구분', 'report_nm': '보고서명', 'flr_nm': '제출인'}, inplace=True)
                 if 'rcept_no' in mj_disclosures.columns:
                    df_disp['Link'] = mj_disclosures['rcept_no'].apply(lambda x: f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={x}")
                 st.dataframe(df_disp, column_config={"Link": st.column_config.LinkColumn("원문 보기")}, use_container_width=True, hide_index=True)
             else:
                 st.info("최근 공시 데이터가 없습니다.")

    elif nav_menu == "📡 IR":
        st.subheader("📡 IR (Investor Relations) 자료실")
        st.markdown(f"**{corp_name}**의 최신 IR 일정 및 발표 자료를 확인하실 수 있습니다.")
        
        st.info("""
        KIND(한국거래소 상장공시시스템) 자료실을 통해 기업의 공식 IR 자료를 확인하세요. 
        아래 버튼을 클릭하면 해당 기업의 IR 자료실 검색 결과로 바로 연결됩니다.
        """)
        
        # KIND IR 자료실 링크 (종목명으로 검색 연결 시도)
        # KIND는 보통 POST 방식이나, 특정 파라미터를 통해 접근 유도가 가능함
        kind_ir_url = "https://kind.krx.co.kr/corpgeneral/irschedule.do?method=searchIRScheduleMain&gubun=iRMaterials"
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.link_button(f"🔗 {corp_name} IR 자료 확인하기 (KIND)", kind_ir_url, use_container_width=True)
        
        with col2:
            st.markdown(f"""
            - **방법**: 링크 접속 후 검색창에 **'{corp_name}'** 입력 후 조회
            - **제공 정보**: IR 일정, 기업설명회 자료(PPT/PDF), 안내 공고 등
            """)
        
        st.divider()
        st.subheader("💡 IR 자료 활용 팁")
        st.write("""
        1. **실적 발표 자료**: 분기별 실적 요약 및 향후 사업 가이던스를 확인하세요.
        2. **기업 설명회(NDR) 자료**: 기업의 핵심 기술력과 중장기 전략이 포함되어 있습니다.
        3. **질의응답(Q&A)**: 공시된 자료 외에 투자자들이 궁금해하는 핵심 쟁점들을 파악할 수 있습니다.
        """)

    elif nav_menu == "📊 증권사리포트":
        st.subheader("📊 증권사 리포트")
        st.info("증권사 기업 분석 리포트 요약 정보를 준비 중입니다.")

    elif nav_menu == "📰 뉴스":
        st.subheader("📰 관련 뉴스")
        st.info("기업 관련 최신 뉴스를 준비 중입니다.")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
    st.exception(e)

