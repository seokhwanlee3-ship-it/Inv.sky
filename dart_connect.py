import os
import requests
import OpenDartReader
from dotenv import load_dotenv

def main():
    # .env 파일 로드
    load_dotenv()
    
    # Windows 콘솔 인코딩 문제 해결
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
    
    # API 키 가져오기
    api_key = os.getenv("DART_API_KEY")
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("[주의] .env 파일에 DART_API_KEY가 설정되지 않았습니다 (기본값).")
        print("      네트워크 연결 확인을 위해 진행하지만, DART API 인증은 실패할 것입니다.")
        # return  <-- 제거: 연결 확인을 위해 진행

    print(f"API Key 확인됨: {api_key[:4]}****")

    # 1. HTTP 상태 코드 확인 (requests 사용)
    # DART 고유번호 요청 URL (가장 기본적인 API)
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {'crtfc_key': api_key}
    
    try:
        print("\n--- 1. HTTP 연결 상태 확인 ---")
        response = requests.get(url, params=params)
        
        # 상태 코드 출력
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("네트워크 연결 성공 (Status 200 OK)")
            
            # API 내부 결과 코드 확인 (DART는 200 OK라도 내부적으로 에러일 수 있음)
            # 간단히 텍스트 앞부분만 확인
            # Encoding handling for Windows console output
            content = response.content.decode('utf-8', errors='replace')[:200]
            if "<err_code>000</err_code>" in content:
                print("DART API 인증 성공 (err_code: 000)")
            else:
                print(f"DART API 인증/요청 실패. 응답 내용 일부:\n{content}")
        else:
            print("네트워크 연결 실패")

    except Exception as e:
        print(f"HTTP 요청 중 오류 발생: {e}")
        return

    # 2. OpenDartReader 라이브러리 테스트
    print("\n--- 2. OpenDartReader 라이브러리 테스트 ---")
    try:
        dart = OpenDartReader(api_key)
        
        # 예시: 삼성전자(005930)의 2023년도 공시 목록 조회
        # 공시 목록이 비어있을 수 있으므로 최근 날짜로 넓게 잡거나 특정 종목 조회
        # 여기서는 가장 최근 공시 5개를 가져와 봅니다.
        print("OpenDartReader 초기화 완료. 삼성전자 공시 목록 조회 시도...")
        
        # corp 확인
        # 삼성전자 종목코드: 005930
        listings = dart.list('005930', start='20240101', kind='A') # 정기공시만 조회
        
        if listings is not None and not listings.empty:
            print("\n[조회 결과]")
            print(listings[['corp_name', 'report_nm', 'rcept_dt']].head())
        else:
            print("\n조회된 공시가 없거나 데이터프레임이 비어있습니다.")
            
    except Exception as e:
        print(f"OpenDartReader 실행 중 오류 발생: {e}")
        print("API 키가 올바른지, 또는 일일 사용 한도를 초과하지 않았는지 확인해주세요.")

if __name__ == "__main__":
    main()
