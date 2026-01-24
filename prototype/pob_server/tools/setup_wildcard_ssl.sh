#!/bin/bash

# 请在运行前填入您的 GoDaddy API 密钥
GD_KEY="YOUR_KEY_HERE"
GD_SECRET="YOUR_SECRET_HERE"

# 创建凭证文件
CRED_FILE=~/.secrets/godaddy.ini
mkdir -p ~/.secrets
echo "dns_godaddy_secret = $GD_SECRET" > $CRED_FILE
echo "dns_godaddy_key = $GD_KEY" >> $CRED_FILE
chmod 600 $CRED_FILE

echo "🚀 Requesting Wildcard SSL for *.infero.net ..."

# 使用 DNS 插件申请泛域名证书
# 注意：这会等待 DNS 传播，可能需要几分钟
sudo certbot certonly \
  --authenticator dns-godaddy \
  --dns-godaddy-credentials $CRED_FILE \
  --dns-godaddy-propagation-seconds 60 \
  -d "infero.net" \
  -d "*.infero.net" \
  --non-interactive --agree-tos --register-unsafely-without-email \
  --keep-until-expiring

if [ $? -eq 0 ]; then
    echo "✅ Wildcard Certificate Obtained!"
    echo "Reloading Nginx..."
    sudo systemctl reload nginx
else
    echo "❌ Certificate request failed."
fi
