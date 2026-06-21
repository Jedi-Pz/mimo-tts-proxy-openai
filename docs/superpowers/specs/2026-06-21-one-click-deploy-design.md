# MIMO TTS Proxy — 一键部署升级

**日期:** 2026-06-21
**状态:** 已确认

## 目标

让 AI agent（Claude Code、Hermes 等）能一条命令全自动部署此代理，用户零感知。
优先 Docker Compose，无 Docker 环境则回退到本地系统服务，均保证开机自启。

## 变更范围

### 新增文件

| 文件 | 用途 |
|---|---|
| `.env.example` | `.env` 模板，仅含 `MIMO_API_KEY=sk-your-key-here` 一行 |
| `Dockerfile` | 构建代理镜像（python:3.12-slim + pip install + 拷代码） |
| `docker-compose.yml` | 编排：build / port 9880 / env_file .env / volume voices.yaml / restart:always |
| `deploy.sh` | 核心部署脚本（见下方流程） |
| `deploy/mimo-tts-proxy.plist` | macOS launchd user agent 模板 |
| `deploy/mimo-tts-proxy.service` | Linux systemd user service 模板 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `mimo_tts_proxy/config.py` | `resolve_api_key()` 改为**只**从 `.env` 读取，读不到则报错退出，不回退系统环境变量 |
| `.gitignore` | 已覆盖 `.env`，无需改动 |

### 用户文件（部署生成，不入 git）

| 文件 | 用途 |
|---|---|
| `.env` | 用户填写 `MIMO_API_KEY=sk-...`，由 deploy.sh 交互生成，`.gitignore` 已确保不入库 |

## 部署流程（deploy.sh）

```
./deploy.sh
  │
  ├─ 1. 检测 Python 3.10+ 和 ffmpeg
  │   ├─ 缺 Python → 报错退出，给出安装指引
  │   └─ 缺 ffmpeg → 报错退出，给出安装指引
  │
  ├─ 2. 检测 .env 是否存在且包含 MIMO_API_KEY
  │   ├─ .env 不存在 → 交互询问"请输入 MIMO API Key"，写入 .env
  │   ├─ .env 存在但 key 为空 → 交互询问，覆盖写入
  │   └─ .env 存在且 key 已填 → 跳过
  │
  ├─ 3. 检测 voices.yaml 是否存在且至少配了一个音色
  │   ├─ 不存在/空 → 交互引导：是否添加音色？（y/n）
  │   │   ├─ y → 问音色名 → 问类型(clone/preset) → 填字段 → 写入 voices.yaml → 继续
  │   │   └─ n → 警告"没有音色，代理将把所有 voice 名当作 MIMO 预置音色透传"
  │   └─ 已有 → 跳过
  │
  ├─ 4. 检测部署环境
  │   ├─ docker 且 docker compose 可用
  │   │   └─ docker compose up -d --build
  │   │       → 容器名 mimo-tts-proxy, restart: always, port 9880
  │   │       → 打印 http://HOST:9880/health 验证
  │   │
  │   └─ docker 不可用 → 本地部署
  │       ├─ macOS
  │       │   → 写 ~/Library/LaunchAgents/com.mimo-tts-proxy.plist
  │       │   → launchctl load ~/Library/LaunchAgents/com.mimo-tts-proxy.plist
  │       │   → plist 中 WorkingDirectory 为项目目录，python -m mimo_tts_proxy.app
  │       │
  │       └─ Linux (systemd)
  │           → 写 ~/.config/systemd/user/mimo-tts-proxy.service
  │           → systemctl --user daemon-reload
  │           → systemctl --user enable --now mimo-tts-proxy.service
  │
  └─ 5. 打印部署结果
      ├─ 部署方式（Docker / macOS launchd / Linux systemd）
      ├─ 测试命令：curl http://127.0.0.1:9880/health
      └─ 开机自启已配置
```

## Dockerfile

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install openai pyyaml
EXPOSE 9880
CMD ["python", "-m", "mimo_tts_proxy.app"]
```

## docker-compose.yml

```yaml
services:
  mimo-tts-proxy:
    build: .
    container_name: mimo-tts-proxy
    restart: always
    ports:
      - "9880:9880"
    env_file:
      - .env
    volumes:
      - ./voices.yaml:/app/voices.yaml:ro
      - ./config.yaml:/app/config.yaml:ro
```

## macOS launchd plist（关键字段）

```xml
<key>Label</key><string>com.mimo-tts-proxy</string>
<key>ProgramArguments</key><array>
    <string>/path/to/venv/bin/python</string>
    <string>-m</string><string>mimo_tts_proxy.app</string>
</array>
<key>WorkingDirectory</key><string>/path/to/project</string>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>EnvironmentVariables</key>
<dict>
    <key>MIMO_TTS_PROXY_DOTENV</key>
    <string>/path/to/project/.env</string>
</dict>
```

## Linux systemd user service（关键字段）

```ini
[Unit]
Description=MIMO TTS Proxy
[Service]
Type=simple
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/python -m mimo_tts_proxy.app
Environment="MIMO_TTS_PROXY_DOTENV=/path/to/project/.env"
Restart=always
[Install]
WantedBy=default.target
```

注意：launchd/systemd 模板中 venv 和项目路径由 deploy.sh 在写文件时替换为实际绝对路径。

## config.py 改动

```python
# resolve_api_key 现行逻辑（读系统环境变量）→ 替换为
def resolve_api_key(section):
    """只从 .env 文件读取 API key，不读系统环境变量。"""
    dotenv_path = os.environ.get("MIMO_TTS_PROXY_DOTENV", BASE_DIR / ".env")
    key = _read_dotenv_key(str(dotenv_path))
    if not key:
        print("未找到 MIMO_API_KEY。请在项目根目录创建 .env 文件，内容为：", file=sys.stderr)
        print("    MIMO_API_KEY=sk-你的key", file=sys.stderr)
        print("或运行 ./deploy.sh 自动生成。", file=sys.stderr)
        sys.exit(1)
    return key
```

`_read_dotenv_key(path)` 读取指定路径的 `.env` 文件，解析 `MIMO_API_KEY=` 行。
`MIMO_TTS_PROXY_DOTENV` 环境变量允许 launchd/systemd/Docker 指定 `.env` 的绝对路径，方便在这些环境下工作目录也不是项目目录时仍能找到 `.env`。

## config.yaml 中 api_key_env 字段

`config.yaml` 中 `mimo.api_key_env` 和 `emotion.api_key_env` 字段**废弃**。保留在文件中但代码不再读取。
新逻辑：`config.py` 的 `resolve_api_key` 忽略 section 参数，只读 `.env`。

## 确认清单

- [x] 只 `.env` 存 key，系统环境变量不读
- [x] Docker 优先，无 Docker 本地部署
- [x] 开机自启（docker restart:always / launchd RunAtLoad+KeepAlive / systemd enable）
- [x] AI agent 一条 `./deploy.sh` 跑完全流程
- [x] `.gitignore` 确保 `.env` 不入库
- [x] `.env.example` 作为模板入 git
- [x] API key 绝不会出现在 git 历史中
