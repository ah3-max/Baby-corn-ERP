# 部署指南

## CI/CD 架構

```
push to main
    ↓
GitHub Actions CI（backend-lint → backend-build + frontend-build）
    ↓（CI 全過）
GitHub Actions Deploy（SSH 連線伺服器 → git pull → docker build → alembic upgrade → restart）
    ↓
健康檢查驗證（/health 回傳 200）
```

---

## GitHub Repository Secrets 設定

到 **Settings → Secrets and variables → Actions → New repository secret** 依序新增：

| Secret 名稱    | 說明                                        | 範例                            |
|----------------|---------------------------------------------|---------------------------------|
| `PROD_HOST`    | 正式伺服器 IP 或域名                         | `192.168.1.100`                 |
| `PROD_USER`    | SSH 登入使用者名稱                           | `ubuntu`                        |
| `PROD_SSH_KEY` | SSH 私鑰（完整內容，含 `-----BEGIN...-----`）| `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `PROD_PORT`    | SSH 端口（選填，預設 22）                    | `22`                            |
| `PROJ_DIR`     | 伺服器上的專案目錄絕對路徑                   | `/opt/babycorn-erp`             |

### 產生 SSH 金鑰對（若尚未建立）

```bash
# 在本機產生
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/babycorn_deploy

# 公鑰貼到伺服器
ssh-copy-id -i ~/.ssh/babycorn_deploy.pub ubuntu@<SERVER_IP>

# 私鑰（~/.ssh/babycorn_deploy 的內容）貼到 PROD_SSH_KEY Secret
cat ~/.ssh/babycorn_deploy
```

---

## GitHub Environment 保護設定（選填但建議）

到 **Settings → Environments → New environment**，建立 `production`：

- **Required reviewers**：指定需要手動審核才能部署的人員
- **Deployment branches**：限定只有 `main` 可以部署

---

## 首次部署流程（伺服器端）

```bash
# 1. 登入伺服器
ssh ubuntu@<SERVER_IP>

# 2. 安裝 Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
newgrp docker

# 3. Clone 專案
git clone git@github.com:<owner>/<repo>.git /opt/babycorn-erp
cd /opt/babycorn-erp

# 4. 設定環境變數
cp .env.example .env
vim .env   # 填入所有必填值

# 5. 啟動服務（首次）
docker compose -f docker-compose.prod.yml up -d

# 6. 初始化 Alembic baseline（資料庫已由 migrations.py 建立）
docker compose -f docker-compose.prod.yml run --rm \
  -e POSTGRES_HOST=db \
  backend \
  alembic stamp b1a2c3d4e5f6

# 7. 初始化資料（角色 + 管理員帳號）
docker compose -f docker-compose.prod.yml run --rm backend python init_data.py
```

---

## Alembic 日常使用

```bash
# 查看目前版本
alembic current

# 查看遷移歷史
alembic history --verbose

# 新增 migration（自動比對 Model 差異）
alembic revision --autogenerate -m "add column xxx to batches"

# 套用到最新版本
alembic upgrade head

# 降版（謹慎使用）
alembic downgrade -1
```

---

## 回滾部署

若新版本有問題，可手動觸發 `workflow_dispatch` 並切換到舊 commit：

```bash
# 在伺服器上快速回滾
cd /opt/babycorn-erp
git log --oneline -10           # 找到上一個穩定 commit
git reset --hard <commit-sha>
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d
```
