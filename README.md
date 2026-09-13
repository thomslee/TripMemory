# 途迹记忆 TripMemory

旅游记忆系统 —— 与「途迹 TripCanvas」联动，记录每一段旅行的美好回忆。

## 项目定位

- **途迹 TripCanvas**：旅游前的规划 + 旅游过程中的行程管理
- **途迹记忆 TripMemory**：旅游结束后的回忆整理、照片归档、AI游记生成、动态展示

## 核心功能

1. **行程定稿同步**：TripCanvas 侧新增「行程定稿」状态（`finalized`），仅定稿行程可同步到 TripMemory（含节点、天气、交通等）。支持**绑定个人 TripCanvas 账号**：同步时使用绑定账号访问 TripCanvas，可同步自己账号下的行程（未绑定时使用服务账号）
2. **照片归档**：对接百度网盘（OAuth 授权持久化），自动提取照片EXIF信息（拍摄时间、地点），按时间60%+距离40%匹配到行程节点
3. **AI游记**：DeepSeek 结合景点特色、天气、照片，生成每个节点的旅游游记文字
4. **游记配音**：edge-tts 免费在线语音，一键批量生成全部节点配音（中文女声，无需API密钥）
5. **动态展示**：沉浸式回忆展示页 —— 照片墙（灯箱查看）+ 游记文字 + 配音连播 + 背景音乐（内置3首）
6. **用户体系**：注册/登录、记忆行程CRUD

## 技术栈

- **前端**：Vue 3 + Vite + Vant + Pinia + Vue Router（端口 5174）
- **后端**：FastAPI + SQLAlchemy + MySQL（端口 8003）
- **外部对接**：TripCanvas API、百度网盘开放平台、DeepSeek 大模型、edge-tts

## 项目结构

```
trip-memory/
├── backend/                 # 后端
│   ├── app/
│   │   ├── main.py         # 应用入口（含 /static 静态资源挂载）
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库连接
│   │   ├── models/         # 数据模型（含 BaiduNetAuth token 持久化）
│   │   ├── routers/        # 路由（auth / memory / baidunet）
│   │   └── services/       # 服务（TripCanvas对接、百度网盘、AI、照片匹配、TTS配音）
│   ├── static/             # 静态资源（audio 配音 / bgm 背景音乐 / sample-photos）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run.py
├── frontend/               # 前端
│   ├── src/
│   │   ├── views/          # 页面（含 Showcase.vue 动态展示页）
│   │   ├── stores/         # 状态管理
│   │   ├── router/         # 路由
│   │   ├── api/            # API封装
│   │   └── style.css       # 全局样式
│   ├── vite.config.ts      # /api、/static 代理到 8003
│   └── package.json
├── deploy/                 # 生产部署产物
│   ├── deploy.sh           # 服务器部署脚本
│   ├── tripmemory-nginx.conf  # nginx 配置（8082）
│   └── .env.production     # 生产环境变量模板
├── docker-compose.yml      # 生产 compose（共享 news-mysql / news_news_net）
└── README.md
```

## 快速开始（本地开发）

### 1. 准备依赖

```bash
# 后端（Python 3.12+）
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 启动服务（需先启动 TripCanvas 后端于 8002）

```bash
# 后端（端口 8003）
cd backend && .venv\Scripts\python.exe run.py

# 前端（端口 5174）
cd frontend && npm run dev
```

访问 http://localhost:5174

### 3. 配置 `backend/.env`

- `TRIPCANVAS_API_URL`：TripCanvas 后端 API 地址
- `TRIPCANVAS_API_TOKEN` / `TRIPCANVAS_SERVICE_USERNAME` / `TRIPCANVAS_SERVICE_PASSWORD`：TripCanvas 访问凭证（token 过期后自动用服务账号续期）
- `BAIDUNET_APP_KEY` / `BAIDUNET_SECRET_KEY`：百度网盘开放平台密钥
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：DeepSeek 大模型配置

### 4. 绑定个人 TripCanvas 账号（可选）

登录 TripMemory 后，进入「用户中心 → TripCanvas 账号绑定」，输入你的 TripCanvas 登录账号密码保存即可。此后同步行程将使用该账号访问 TripCanvas，可以同步你自己账号下已定稿的行程；未绑定时仅能同步服务账号的行程。绑定密码使用 `SECRET_KEY` 派生密钥加密存储。

## 与 TripCanvas 的联动流程

1. 在 TripCanvas 中规划/生成行程
2. 行程无时间线冲突后，点击详情页「**行程定稿**」（状态变为"已定稿"，含冲突校验，无法定稿时会提示原因）
3. 在 TripMemory「用户中心 → TripCanvas 账号绑定」绑定你的 TripCanvas 账号（若行程归属该账号）
4. 在 TripMemory 首页「从途迹同步」输入行程ID，仅定稿行程可同步
5. 百度网盘授权 → 选择照片文件夹 → 批量同步 → 自动匹配到行程节点
6. 详情页「AI生成游记」→「生成全部配音」
7. 进入「**动态展示**」页：照片墙 + 游记朗读 + 背景音乐 + 自动连播

## 生产部署（腾讯云 82.156.177.145）

服务器与 TripCanvas 共用（TripCanvas 前端 8081 / 后端 8002，TripMemory 前端 8082 / 后端 8003）。

```bash
# 1. 本地构建前端
cd frontend && npm run build

# 2. 上传代码到服务器 ~/tripmemory（deploy/deploy.sh 可参考）
# 3. 服务器上执行
cd ~/tripmemory
cp deploy/.env.production .env   # 按需修改密钥
docker compose build backend
docker exec news-mysql mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS trip_memory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
docker compose up -d backend

# 4. 部署前端 + nginx
sudo cp deploy/tripmemory-nginx.conf /etc/nginx/conf.d/tripmemory.conf
sudo nginx -t && sudo nginx -s reload
```

**注意**：
- TripCanvas 后端须先部署并包含「行程定稿」接口（`POST /api/trips/{id}/finalize`）
- TripMemory 容器通过 docker 网络 `news_news_net` 直连 `trip-backend:8002`（compose 内已配置）
- 生产环境 DeepSeek 密钥、百度网盘 Redirect URI 等需在服务器 `.env` 中配置

## 数据模型

- **User**：用户
- **MemoryTrip**：记忆行程（关联TripCanvas行程ID）
- **MemoryNode**：行程节点（地点、时间、天气、游记、音频）
- **MemoryPhoto**：照片元数据（百度网盘文件ID、EXIF、匹配状态）
- **BaiduNetAuth**：百度网盘 OAuth token 持久化（照片代理展示用）

## License

MIT
