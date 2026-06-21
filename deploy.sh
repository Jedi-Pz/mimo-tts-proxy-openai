#!/usr/bin/env bash
# MIMO TTS Proxy — 一键部署脚本
# 用法: ./deploy.sh
# AI agent 或普通用户均可执行。自动检测 Docker / macOS / Linux 并选择最佳部署方式。
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  MIMO TTS Proxy — 一键部署${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# ── 1. 前置检测 ────────────────────────────────────────────────

check_prereqs() {
    echo -e "${BOLD}检测运行环境...${NC}"

    # Python
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}✗ 未找到 python3${NC}"
        echo "  安装方法:"
        echo "    macOS:  brew install python"
        echo "    Linux:  apt install python3"
        echo "    官网:   https://www.python.org/downloads/"
        exit 1
    fi
    local py_ver
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "  ${GREEN}✓${NC} Python $py_ver"

    # ffmpeg
    if ! command -v ffmpeg &>/dev/null; then
        echo -e "${RED}✗ 未找到 ffmpeg${NC}"
        echo "  安装方法:"
        echo "    macOS:  brew install ffmpeg"
        echo "    Linux:  apt install ffmpeg"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} ffmpeg"
}

# ── 2. .env 配置 ───────────────────────────────────────────────

setup_dotenv() {
    echo ""
    echo -e "${BOLD}配置 MIMO API Key...${NC}"

    local key=""
    if [ -f .env ]; then
        key=$(grep '^MIMO_API_KEY=' .env 2>/dev/null | sed 's/^MIMO_API_KEY=//' | tr -d '"'"'"' || true)
        if [ -n "$key" ] && [ "$key" != "sk-your-key-here" ]; then
            echo -e "  ${GREEN}✓${NC} .env 已配置"
            return
        fi
    fi

    echo "  在 https://xiaomimimo.com 注册获取 API Key"
    echo ""
    read -r -p "  请输入 MIMO API Key (sk-...): " key
    if [ -z "$key" ]; then
        echo -e "${RED}✗ API Key 不能为空，部署中止${NC}"
        exit 1
    fi
    echo "MIMO_API_KEY=$key" > .env
    chmod 600 .env
    echo -e "  ${GREEN}✓${NC} .env 已创建"
}

# ── 3. voices.yaml 检测 ────────────────────────────────────────

setup_voices() {
    echo ""
    echo -e "${BOLD}检测音色配置...${NC}"

    if [ -f voices.yaml ] && grep -qE '^  [a-zA-Z]' voices.yaml 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} voices.yaml 已配置"
        return
    fi

    echo -e "  ${YELLOW}voices.yaml 未配置音色${NC}"
    echo "  所有 voice 名将被当作 MIMO 预置音色名称直接透传。"
    echo "  如需在部署完成后添加音色，编辑 voices.yaml 后重启服务即可。"
}

# ── 4. 部署 ────────────────────────────────────────────────────

deploy() {
    echo ""
    echo -e "${BOLD}选择部署方式...${NC}"

    # 创建 venv（无论哪种方式都需要，Docker 由 build 自己管）
    if [ ! -d venv ]; then
        echo "  创建 Python 虚拟环境..."
        python3 -m venv venv
    fi
    # 确保 venv 里的依赖就绪（本地部署需要）
    ./venv/bin/pip install -q openai pyyaml

    if command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
        echo -e "  ${GREEN}→${NC} Docker 可用，使用 Docker Compose 部署"
        deploy_docker
    else
        echo -e "  ${YELLOW}→${NC} Docker 不可用，使用本地系统服务部署"
        deploy_local
    fi
}

deploy_docker() {
    docker compose up -d --build
    echo ""
    echo -e "${BOLD}${GREEN}部署完成 ✓${NC}"
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  方式: Docker Compose                       │"
    echo "  │  容器: mimo-tts-proxy                       │"
    echo "  │  端口: 9880                                 │"
    echo "  │  重启: always（开机自启）                    │"
    echo "  ├─────────────────────────────────────────────┤"
    echo "  │  测试: curl http://127.0.0.1:9880/health    │"
    echo "  │  日志: docker compose logs -f               │"
    echo "  │  停止: docker compose down                  │"
    echo "  └─────────────────────────────────────────────┘"
}

deploy_local() {
    local os_type
    os_type="$(uname -s)"
    local venv_python="$PROJECT_DIR/venv/bin/python"

    if [ "$os_type" = "Darwin" ]; then
        deploy_macos "$venv_python"
    elif [ "$os_type" = "Linux" ]; then
        deploy_linux "$venv_python"
    else
        echo -e "${RED}✗ 不支持的操作系统: $os_type${NC}"
        echo "  请手动运行: python -m mimo_tts_proxy.app"
        exit 1
    fi
}

deploy_macos() {
    local venv_python="$1"
    local plist_path="$HOME/Library/LaunchAgents/com.mimo-tts-proxy.plist"

    # 先停止已存在的服务
    launchctl unload "$plist_path" 2>/dev/null || true

    # 从模板写入 plist
    sed -e "s|{{VENV_PYTHON}}|$venv_python|g" \
        -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
        deploy/mimo-tts-proxy.plist > "$plist_path"

    launchctl load "$plist_path"

    echo ""
    echo -e "${BOLD}${GREEN}部署完成 ✓${NC}"
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  方式: macOS launchd（开机自启）             │"
    echo "  │  配置: $plist_path"
    echo "  │  端口: 9880                                 │"
    echo "  ├─────────────────────────────────────────────┤"
    echo "  │  测试: curl http://127.0.0.1:9880/health    │"
    echo "  │  日志: tail -f $PROJECT_DIR/proxy.log       │"
    echo "  │  停止: launchctl unload $plist_path          │"
    echo "  └─────────────────────────────────────────────┘"
}

deploy_linux() {
    local venv_python="$1"
    local service_dir="$HOME/.config/systemd/user"
    local service_path="$service_dir/mimo-tts-proxy.service"

    mkdir -p "$service_dir"

    # 先停止已存在的服务
    systemctl --user stop mimo-tts-proxy.service 2>/dev/null || true

    # 从模板写入
    sed -e "s|{{VENV_PYTHON}}|$venv_python|g" \
        -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
        deploy/mimo-tts-proxy.service > "$service_path"

    systemctl --user daemon-reload
    systemctl --user enable --now mimo-tts-proxy.service

    echo ""
    echo -e "${BOLD}${GREEN}部署完成 ✓${NC}"
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  方式: Linux systemd（开机自启）             │"
    echo "  │  配置: $service_path"
    echo "  │  端口: 9880                                 │"
    echo "  ├─────────────────────────────────────────────┤"
    echo "  │  测试: curl http://127.0.0.1:9880/health    │"
    echo "  │  日志: journalctl --user -u mimo-tts-proxy -f│"
    echo "  │  停止: systemctl --user stop mimo-tts-proxy │"
    echo "  └─────────────────────────────────────────────┘"
}

# ── 主流程 ─────────────────────────────────────────────────────

check_prereqs
setup_dotenv
setup_voices
deploy
