import OpenDartReader
import os
import pandas as pd
from dotenv import load_dotenv

print(f"Pandas version: {pd.__version__}")

load_dotenv()
api_key = os.getenv("DART_API_KEY")
dart = OpenDartReader(api_key)

try:
    print("Attempting to find corp code for '삼성전자'...")
    code = dart.find_corp_code("삼성전자")
    print(f"Result: {code}")
except Exception as e:
    print(f"Error caught: {e}")
    print(f"Error type: {type(e)}")
