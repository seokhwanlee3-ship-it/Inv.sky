import OpenDartReader
import pandas as pd
import os
import datetime
from dotenv import load_dotenv

class DartHandler:
    def __init__(self, api_key=None):
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("DART_API_KEY")
        
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API Key is missing. Please check .env file.")
        
        self.dart = OpenDartReader(self.api_key)

    def find_corp_code(self, corp_name):
        try:
            return self.dart.find_corp_code(corp_name)
        except:
            return None

    def get_financial_data(self, corp_code, year, reprt_code):
        """
        특정 연도/분기의 재무제표를 조회하여 핵심 지표(매출, 영업이익, 순이익)를 반환합니다.
        누적 데이터인지 여부는 DART가 제공하는 값에 따르며, 이 함수는 원본 값을 그대로 반환합니다.
        """
        try:
            # finstate 호출 (fs_div 인자 제거)
            fs_all = self.dart.finstate(corp_code, year, reprt_code=reprt_code)
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

        if fs_all is None or fs_all.empty:
            return None

        # 연결(CFS) 우선, 없으면 별도(OFS)
        if 'fs_div' in fs_all.columns:
            fs = fs_all[fs_all['fs_div'] == 'CFS']
            if fs.empty:
                fs = fs_all[fs_all['fs_div'] == 'OFS']
        else:
            # fs_div 컬럼이 없는 경우 (매우 드묾)
            fs = fs_all

        if fs.empty:
            return None

        # 계정명 매핑 (DART 표준 계정코드 활용 권장이나, 이름 매칭 병행)
        # 매출액: ifRS-full_Revenue
        # 영업이익: dart_OperatingIncomeLoss
        # 당기순이익: ifRS-full_ProfitLoss
        
        def get_value(df, account_names):
            for nm in account_names:
                # account_nm 컬럼에서 포함 여부 확인
                row = df[df['account_nm'].str.contains(nm, na=False)]
                if not row.empty:
                    val = row.iloc[0]['thstrm_amount'] # 당기 금액
                    if val == '-': return 0
                    try:
                        return float(val.replace(',', ''))
                    except:
                        return 0
            return 0

        revenue = get_value(fs, ['매출액', '수익(매출액)'])
        op_income = get_value(fs, ['영업이익', '영업손실'])
        net_income = get_value(fs, ['당기순이익', '당기순손실', '분기순이익', '반기순이익'])
        
        # 상세 테이블용 전체 데이터도 반환하면 좋음
        return {
            'revenue': revenue,
            'op_income': op_income,
            'net_income': net_income,
            'details': fs # 전체 데이터프레임
        }

    def get_stock_code(self, corp_name):
        """
        상장 종목 코드를 반환 (FinanceDataReader용)
        OpenDartReader의 list() 메서드나 corp_codes를 활용
        """
        # 간단하게 dart.corp_codes에서 검색
        # (주의: OpenDartReader 객체 초기화 시 corp_codes를 로딩함)
        # 하지만 이게 오래 걸릴 수 있으므로, find_corp_code로 찾은 뒤
        # 해당 종목의 stock_code를 별도로 조회하는 게 나을 수 있음.
        # 여기서는 편의상 document(공시정보) 조회 시 나오는 stock_code를 활용하거나
        # dart.find_corp_code 결과는 DART 고유코드임.
        
        # OpenDartReader API에는 종목코드를 바로 주는 명시적 함수가 find_corp_code(고유코드 반환) 외에
        # 기업개황(company_by_name) 등을 쓸 수 있음.
        try:
            info = self.dart.company(corp_name)
            if info:
                return info.get('stock_code')
        except:
            pass
        return None

    def get_recent_disclosures(self, corp_code, count=15):
        """
        특정 기업의 최근 공시 목록을 가져옵니다.
        """
        try:
            # 최근 1년 치 조회
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
            
            # API 호출
            disclosures = self.dart.list(corp_code, start=start_date)
            
            if disclosures is None or disclosures.empty:
                return None
                
            return disclosures.head(count)
        except Exception as e:
            # 앱에서 에러를 확인할 수 있도록 예외를 다시 발생시킵니다.
            raise e
