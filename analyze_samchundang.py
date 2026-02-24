import OpenDartReader
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. 설정 및 초기화
# -----------------------------------------------------------------------------
# .env 파일 로드
load_dotenv()
api_key = os.getenv("DART_API_KEY")

if not api_key:
    print("Error: API Key가 없습니다. .env 파일을 확인해주세요.")
    exit(1)

# OpenDartReader 객체 생성
dart = OpenDartReader(api_key)

# 종목코드 찾기
corp_name = "삼천당제약"
try:
    corp_code = dart.find_corp_code(corp_name)
    print(f"'{corp_name}'의 종목코드: {corp_code}")
except Exception as e:
    print(f"종목코드를 찾을 수 없습니다: {e}")
    exit(1)

# -----------------------------------------------------------------------------
# 2. 데이터 수집 (최근 5년: 2020~2024)
# -----------------------------------------------------------------------------
print("데이터 수집 시작 (2020 ~ 2024)...")

data_list = []
years = range(2020, 2025) # 2020, 2021, 2022, 2023, 2024
quarters = ['11013', '11012', '11014', '11011'] # 1Q, 半期(2Q누적), 3Q(3Q누적), 사업(4Q누적)

for year in years:
    for reprt_code in quarters:
        try:
            # 재무제표 조회 (연결재무제표 우선)
            # finstate는 fs_div인자를 받지 않고, 결과 DataFrame에 fs_div 컬럼이 있음
            try:
                fs_all = dart.finstate(corp_code, year, reprt_code=reprt_code)
            except Exception as e:
                # 데이터가 없는 경우 등
                print(f"{year}년 {reprt_code}: 데이터 없음 또는 에러 ({e})")
                continue

            if fs_all is None or fs_all.empty:
                continue

            # 연결(CFS) 우선, 없으면 별도(OFS)
            fs = fs_all[fs_all['fs_div'] == 'CFS']
            if fs.empty:
                fs = fs_all[fs_all['fs_div'] == 'OFS']
            
            if fs.empty:
                continue

            # 필요한 계정 추출 (매출액, 영업이익, 당기순이익)
            # 계정명은 표준 계정코드(account_id)를 사용하는 것이 안전함
            # 매출액: ifRS-full_Revenue, 영업이익: dart_OperatingIncomeLoss, 당기순이익: ifRS-full_ProfitLoss
            # 하지만 OpenDartReader는 account_nm을 주로 사용.
            
            # 필터링 함수
            def get_amount(df, account_names):
                # account_nm에 keyword가 포함된 행 찾기
                for nm in account_names:
                    row = df[df['account_nm'].str.contains(nm, na=False)]
                    if not row.empty:
                        # thstrm_amount: 당기 금액 (누적일 수 있음)
                        # 일부 보고서는 'thstrm_amount'가 콤마 건너뜀 문자열임
                        val = row.iloc[0]['thstrm_amount']
                        if val == '-': return 0
                        return float(val.replace(',', ''))
                return 0

            # 3개월(당분기) 데이터가 별도로 표기되는지 확인 필요.
            # 하지만 DART API finstate는 보통 'thstrm_amount'에
            # 1Q: 3개월
            # 2Q(반기): 6개월 누적
            # 3Q: 9개월 누적
            # 4Q(사업): 1년 누적
            # 값을 줍니다. 따라서 누적값을 가져와서 나중에 차감 계산합니다.
            
            revenue = get_amount(fs, ['매출액', '수익(매출액)'])
            op_income = get_amount(fs, ['영업이익', '영업손실']) # 손실도 영업이익 계정에 포함됨
            net_income = get_amount(fs, ['당기순이익', '당기순손실', '분기순이익', '반기순이익'])

            # 분기 구분 (1Q, 2Q, 3Q, 4Q)
            q_map = {'11013': 1, '11012': 2, '11014': 3, '11011': 4}
            quarter_num = q_map[reprt_code]

            data_list.append({
                'Year': year,
                'Quarter': quarter_num,
                'Revenue_Acc': revenue,     # 누적
                'OpIncome_Acc': op_income,  # 누적
                'NetIncome_Acc': net_income # 누적
            })
            print(f"{year}년 {quarter_num}분기 데이터 수집 완료")

        except Exception as e:
            print(f"{year}년 {reprt_code} 처리 중 오류: {e}")

df = pd.DataFrame(data_list)
if df.empty:
    print("수집된 데이터가 없습니다.")
    exit(1)

# 정렬
df = df.sort_values(by=['Year', 'Quarter'])

# -----------------------------------------------------------------------------
# 3. 데이터 가공 (누적 -> 분기별 별도 실적)
# -----------------------------------------------------------------------------
# 각 연도별로 순회하며 차감
df['Revenue'] = 0.0
df['OpIncome'] = 0.0
df['NetIncome'] = 0.0

for year in years:
    year_data = df[df['Year'] == year]
    if year_data.empty: continue
    
    # 1Q는 그대로
    q1 = year_data[year_data['Quarter'] == 1]
    if not q1.empty:
        idx = q1.index[0]
        df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc']
        df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc']
        df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc']
        
    # 2Q = 2Q누적 - 1Q누적
    q2 = year_data[year_data['Quarter'] == 2]
    if not q2.empty:
        idx = q2.index[0]
        prev = year_data[year_data['Quarter'] == 1]
        if not prev.empty:
            df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc'] - prev.iloc[0]['Revenue_Acc']
            df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc'] - prev.iloc[0]['OpIncome_Acc']
            df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc'] - prev.iloc[0]['NetIncome_Acc']
        else:
            # 1Q 데이터가 없으면 누적값을 그대로 쓸 수 밖에 없음 (또는 NaN 처리)
            # 여기선 그대로 둠
            df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc']
            df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc']
            df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc']

    # 3Q = 3Q누적 - 2Q누적
    q3 = year_data[year_data['Quarter'] == 3]
    if not q3.empty:
        idx = q3.index[0]
        prev = year_data[year_data['Quarter'] == 2]
        if not prev.empty:
            df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc'] - prev.iloc[0]['Revenue_Acc']
            df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc'] - prev.iloc[0]['OpIncome_Acc']
            df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc'] - prev.iloc[0]['NetIncome_Acc']
    
    # 4Q = 4Q누적 - 3Q누적
    q4 = year_data[year_data['Quarter'] == 4]
    if not q4.empty:
        idx = q4.index[0]
        prev = year_data[year_data['Quarter'] == 3]
        if not prev.empty:
            df.at[idx, 'Revenue'] = df.at[idx, 'Revenue_Acc'] - prev.iloc[0]['Revenue_Acc']
            df.at[idx, 'OpIncome'] = df.at[idx, 'OpIncome_Acc'] - prev.iloc[0]['OpIncome_Acc']
            df.at[idx, 'NetIncome'] = df.at[idx, 'NetIncome_Acc'] - prev.iloc[0]['NetIncome_Acc']

# -----------------------------------------------------------------------------
# 4. 전년 동기 대비 증감율(YoY) 계산
# -----------------------------------------------------------------------------
# Period 컬럼 생성 (예: '2020.1Q')
df['Period'] = df['Year'].astype(str) + "." + df['Quarter'].astype(str) + "Q"

# Shift 4 (4분기 전 데이터와 비교)
df['Rev_YoY'] = df['Revenue'].pct_change(periods=4) * 100
df['Op_YoY'] = df['OpIncome'].pct_change(periods=4) * 100
df['Net_YoY'] = df['NetIncome'].pct_change(periods=4) * 100

# -----------------------------------------------------------------------------
# 5. 시각화
# -----------------------------------------------------------------------------
print("시각화 생성 중...")

# 한글 폰트 설정 (Windows 기본 폰트)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 캔버스 설정
fig, axes = plt.subplots(3, 1, figsize=(14, 18))
plt.subplots_adjust(hspace=0.4)

accounts = [
    ('Revenue', 'Rev_YoY', '매출액'),
    ('OpIncome', 'Op_YoY', '영업이익'),
    ('NetIncome', 'Net_YoY', '당기순이익')
]

for i, (acc, acc_yoy, title) in enumerate(accounts):
    ax1 = axes[i]
    
    # 막대 그래프 (금액) - 단위: 억 원
    bars = ax1.bar(df['Period'], df[acc] / 100000000, color='#4e79a7', alpha=0.7, label='금액 (억 원)')
    ax1.set_ylabel('금액 (억 원)', color='#4e79a7', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#4e79a7')
    ax1.set_title(f"삼천당제약 분기별 {title} 추이 (최근 5년)", fontsize=14, fontweight='bold')
    
    # x축 레이블 회전
    ax1.set_xticklabels(df['Period'], rotation=45)
    
    # 막대 위에 값 표시
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, height, f'{int(height)}', ha='center', va='bottom', fontsize=9)

    # 선 그래프 (증감율) - 보조축
    ax2 = ax1.twinx()
    line = ax2.plot(df['Period'], df[acc_yoy], color='#e15759', marker='o', linewidth=2, label='전년 동기 대비 증감율 (%)')
    ax2.set_ylabel('증감율 (%)', color='#e15759', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#e15759')
    ax2.axhline(0, color='gray', linestyle='--', linewidth=0.8) # 0% 기준선

    # 증감율 값 표시 (너무 복잡할 수 있으니 주요 포인트만 표시하거나 생략 가능, 여기선 표시)
    for j, txt in enumerate(df[acc_yoy]):
        if pd.notna(txt):
            ax2.text(j, txt, f'{txt:.1f}%', ha='center', va='bottom' if txt > 0 else 'top', color='#e15759', fontsize=9)

    # 범례 (두 축 합치기)
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

# 저장 및 표시
output_file = 'samchundang_financials.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"그래프 저장 완료: {output_file}")

# 데이터도 CSV로 저장
csv_file = 'samchundang_financials.csv'
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"데이터 저장 완료: {csv_file}")
