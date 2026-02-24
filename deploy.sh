#!/bin/bash
# deploy.sh - 서버에서 코드 업데이트 시 사용
set -e

echo "=== Stock Bot 배포 업데이트 ==="
cd /home/ubuntu/stock-bot

echo "[1/3] 최신 코드 가져오기..."
git pull origin main

echo "[2/3] 패키지 업데이트..."
pip3 install -r requirements.txt --quiet

echo "[3/3] 봇 서비스 재시작..."
sudo systemctl restart stockbot
sudo systemctl status stockbot --no-pager

echo "=== 배포 완료! ==="
