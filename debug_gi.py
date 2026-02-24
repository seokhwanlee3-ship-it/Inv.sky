import OpenDartReader
import os
import pandas as pd
from dotenv import load_dotenv
import datetime

load_dotenv()
api_key = os.getenv("DART_API_KEY")
dart = OpenDartReader(api_key)

corp_name = "지아이이노베이션"

try:
    print(f"Finding code for {corp_name}...")
    code = dart.find_corp_code(corp_name)
    print(f"Corp Code: {code}")

    if code:
        # Try 1 year
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        print(f"Fetching list since {start_date}...")
        
        # Test default list (3 months default usually)
        # d1 = dart.list(code) 
        # print(f"Default list count: {len(d1) if d1 is not None else 0}")
        
        # Test 1 year
        d2 = dart.list(code, start=start_date)
        if d2 is not None:
            print(f"1 Year list count: {len(d2)}")
            print(d2.head())
        else:
            print("1 Year list is Empty or None")
            
        # Try longer if empty
        if d2 is None or d2.empty:
            start_date_2 = (datetime.datetime.now() - datetime.timedelta(days=365*2)).strftime("%Y-%m-%d")
            print(f"Fetching list since {start_date_2}...")
            d3 = dart.list(code, start=start_date_2)
            if d3 is not None:
                print(f"2 Year list count: {len(d3)}")
            else:
                print("2 Year list is Empty")

except Exception as e:
    print(f"Error: {e}")
