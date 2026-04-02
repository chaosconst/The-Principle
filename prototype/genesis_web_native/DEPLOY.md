# 部署说明

服务器：`ubuntu@54.168.240.219`，SSH key：`~/.ssh/ec2_tokyo_2023.pem`

---

## 环境总览

| 环境 | 访问地址 | Git 分支 | 前端目录 | API Relay 端口 |
|------|---------|---------|---------|---------------|
| **Prod** | https://infero.net/genesis | `main` | `/home/ubuntu/The-Principle/prototype/genesis_web_native/` | 8080 |
| **Dev** | https://dev.infero.net/genesis | `dev` | `/home/ubuntu/The-Principle-dev/prototype/genesis_web_native/` | 8084 |

---

## 服务列表

### 1. API Relay（LLM 代理）

| 环境 | 目录 | 端口 | 进程 |
|------|------|------|------|
| Prod | `/home/ubuntu/pob_server/relay_service/` | 8080 | `python3 relay_server.py` |
| Dev | `/home/ubuntu/pob_server/relay_service.dev/` | 8084 | `python3 relay_server.py` |

启动方式：
```bash
# Prod
cd /home/ubuntu/pob_server/relay_service
PORT=8080 HTML_PATH=/home/ubuntu/The-Principle/prototype/genesis_web_native/index.html \
  nohup python3 relay_server.py > relay.log 2>&1 &

# Dev
cd /home/ubuntu/pob_server/relay_service.dev
PORT=8084 HTML_PATH=/home/ubuntu/The-Principle-dev/prototype/genesis_web_native/index.html \
  nohup python3 relay_server.py > relay.log 2>&1 &
```

---

### 2. Device Relay（设备 WebSocket 中继）

各环境独立。

| 环境 | 目录 | HTTP 端口 | WS 端口 |
|------|------|----------|---------|
| Prod | `/home/ubuntu/device_relay/` | 8082 | 8083 |
| Dev | `/home/ubuntu/device_relay_dev/` | 8087 | 8088 |

启动方式：
```bash
# Prod
cd /home/ubuntu/device_relay
HTTP_PORT=8082 WS_PORT=8083 RELAY_WS_URL=wss://infero.net/device-relay/ws \
  nohup python3 relay.py >> relay.log 2>&1 &

# Dev
cd /home/ubuntu/device_relay_dev
HTTP_PORT=8087 WS_PORT=8088 RELAY_WS_URL=wss://dev.infero.net/device-relay/ws \
  nohup python3 relay.py >> relay.log 2>&1 &
```

日志：`relay.log`（各自目录下）

Git 同步（与对应分支保持一致）：
```bash
# Prod device relay ← main 分支
cp /home/ubuntu/The-Principle/prototype/device_relay/relay.py /home/ubuntu/device_relay/relay.py

# Dev device relay ← dev 分支
cp /home/ubuntu/The-Principle-dev/prototype/device_relay/relay.py /home/ubuntu/device_relay_dev/relay.py
# 然后重启对应实例
```

---

## 开发工作流

### 日常开发
```bash
# 本地切到 dev 分支
git checkout dev

# 开发、提交
git add ...
git commit -m "..."
git push origin dev

# 服务器更新 dev 前端（热重载，无需重启）
ssh -i ~/.ssh/ec2_tokyo_2023.pem ubuntu@54.168.240.219 \
  "cd /home/ubuntu/The-Principle-dev && git pull origin dev"
```

### 合并到 Prod
```bash
# 本地 dev 合并到 main
git checkout main
git merge dev
git push origin main

# 服务器更新 prod 前端（热重载，无需重启）
ssh -i ~/.ssh/ec2_tokyo_2023.pem ubuntu@54.168.240.219 \
  "cd /home/ubuntu/The-Principle && git pull origin main"
```

### API Relay 有改动时需要重启
```bash
# 停掉旧进程，重新启动
ssh -i ~/.ssh/ec2_tokyo_2023.pem ubuntu@54.168.240.219 "
  pkill -f 'relay_service/relay_server.py'  # 或 relay_service.dev
  cd /home/ubuntu/pob_server/relay_service
  PORT=8080 HTML_PATH=... nohup python3 relay_server.py > relay.log 2>&1 &
"
```

---

## 一键 SSH 进服务器

```bash
ssh -i ~/.ssh/ec2_tokyo_2023.pem ubuntu@54.168.240.219
```

## 查看服务状态

```bash
# 检查所有 relay 端口
lsof -ti:8080 && echo 'prod api relay up'
lsof -ti:8082 && echo 'prod device relay http up'
lsof -ti:8083 && echo 'prod device relay ws up'
lsof -ti:8084 && echo 'dev api relay up'
lsof -ti:8087 && echo 'dev device relay http up'
lsof -ti:8088 && echo 'dev device relay ws up'

# 查看日志
tail -f /home/ubuntu/pob_server/relay_service/relay.log       # prod api relay
tail -f /home/ubuntu/pob_server/relay_service.dev/relay.log   # dev api relay
tail -f /home/ubuntu/device_relay/relay.log                    # prod device relay
tail -f /home/ubuntu/device_relay_dev/relay.log               # dev device relay
```
