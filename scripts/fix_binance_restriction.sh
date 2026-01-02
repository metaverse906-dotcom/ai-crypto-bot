#!/bin/bash
# 快速修复：替换 Binance 为 OKX（无地区限制）

cd ~/ai-crypto-bot

# 备份
cp core/mvrv_data_source.py core/mvrv_data_source.py.backup
cp bot/handlers/mvrv_dca_analyzer.py bot/handlers/mvrv_dca_analyzer.py.backup

# 替换
sed -i 's/ccxt.binance()/ccxt.okx()/g' core/mvrv_data_source.py
sed -i 's/ccxt.binance()/ccxt.okx()/g' bot/handlers/mvrv_dca_analyzer.py
sed -i "s/'BTC\/USDT'/'BTC\/USDT:USDT'/g" core/mvrv_data_source.py
sed -i "s/'BTC\/USDT'/'BTC\/USDT:USDT'/g' bot/handlers/mvrv_dca_analyzer.py

echo "✅ 已切换到 OKX 交易所"
echo "重启 bot: python bot_main.py"
