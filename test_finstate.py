import OpenDartReader
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DART_API_KEY")
dart = OpenDartReader(api_key)

print("Testing finstate...")
try:
    # 2023 1Q data for Samchundang Pharm (000250) - corp_code needs to be found first
    corp_code = dart.find_corp_code("삼천당제약")
    fs = dart.finstate(corp_code, 2023, reprt_code='11013') # 1Q
    
    if fs is not None:
        print("Columns:", fs.columns)
        print("Head:", fs.head())
        if 'fs_div' in fs.columns:
            print("fs_div values:", fs['fs_div'].unique())
    else:
        print("No data returned")

except Exception as e:
    print("Error:", e)
