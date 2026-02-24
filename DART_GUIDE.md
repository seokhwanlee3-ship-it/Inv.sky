# DART API 연결 가이드

이 폴더(`stock`)에 DART API 연결을 위한 스크립트와 설정 파일이 있습니다.

## 파일 설명

- `dart_connect.py`: DART API 연결 및 공시 목록 조회 테스트 스크립트
- `.env`: API 키를 저장하는 설정 파일 (숨김 파일일 수 있음)

## 실행 방법

터미널에서 이 폴더(`stock`)로 이동한 후 아래 명령어로 실행하세요.

```powershell
& "C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" dart_connect.py
```
(또는 Python이 환경 변수에 등록된 경우 `python dart_connect.py`)

## 실행 결과

정상적으로 설정되었다면 다음과 같이 출력됩니다.
1. **HTTP Status Code: 200** (서버 연결 성공)
2. **삼성전자 공시 목록** 데이터 출력 (API 인증 성공)

## 주의사항

- `.env` 파일에 `DART_API_KEY`가 올바르게 입력되어 있어야 합니다.
- `opendartreader`, `python-dotenv`, `requests` 라이브러리가 설치되어 있어야 합니다.
  (`pip install opendartreader python-dotenv requests`)
