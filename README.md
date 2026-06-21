# mimo-tts-proxy-openai

一个兼容 OpenAI `/v1/audio/speech` 协议的 HTTP 代理，后端对接**小米 MIMO TTS（MiMo V2.5）**。  
把任意 OpenAI-TTS 客户端指向这个代理，就能用**克隆的游戏角色音色**或 MIMO 预置音色合成语音。

> 📖 [English README](README.en.md)

## 架构

```
OpenAI-TTS 客户端（OpenClaw / Hermes / OpenAI SDK / 任意）
        │
        │  POST /v1/audio/speech
        │  {"model": "tts-1", "input": "...", "voice": "zhuangfangyi", "response_format": "mp3"}
        ▼
┌─────────────────────────────┐
│   mimo-tts-proxy            │
│   http://127.0.0.1:9880     │
│                             │
│  1. 解析音色                 │  voices.yaml → 克隆样本或预置名
│  2. 推断情绪（可选）          │  LLM 读文本，输出一句话风格提示
│  3. 构造 MIMO 请求           │  chat-completions + audio.voice
│  4. 调用 MIMO 合成           │  → 返回 base64 WAV
│  5. 转码（可选）              │  ffmpeg: WAV → mp3/opus/flac/aac/ogg
│  6. 返回音频流               │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│   小米 MIMO API              │
│   api.xiaomimimo.com/v1     │
│                             │
│  TTS 走的是 chat-completions │
│  端点，不是 /v1/audio/speech │
│  这个代理负责做协议翻译       │
└─────────────────────────────┘
```

## 原理

MIMO 把 TTS 作为一个 **chat-completions** 调用来暴露：要朗读的文字放在 `assistant` 消息里，可选的风格指导放在前面的 `user` 消息里，音色（预置名称或克隆样本的 `data:` URL）则通过 `audio.voice` 字段传入。返回的音频是 base64 编码的 WAV，在 `choices[0].message.audio.data` 里。

这个代理对外实现标准的 **OpenAI `/v1/audio/speech`** 接口，对内把每个请求翻译成 MIMO 的 chat-completions 格式。翻译过程包括：

- **音色解析**：注册音色（`voices.yaml`）会被解析为克隆样本的 data-URL 或 MIMO 预置名称；未注册的名称直接作为预置名称透传。
- **情绪推断**（可选，按音色开关）：一个小而快的 LLM 阅读待朗读的文字，输出一句中文"导演"指令（如 `语调上扬，带着惊喜` / `低沉缓慢，略带悲伤` …），和音色的基础风格拼接后作为 MIMO 的 `user` 消息。
- **格式转码**：MIMO 始终返回 WAV；如果客户端请求了 `mp3`、`opus`、`ogg`、`flac`、`aac` 或 `pcm`，就用 ffmpeg 转码后返回。

## 前置条件

| 条件 | 检查方式 | 安装方式 |
|---|---|---|
| **Python ≥ 3.10** | `python3 --version` | [python.org](https://www.python.org/) 或 `brew install python` / `apt install python3` |
| **ffmpeg** | `ffmpeg -version` | `brew install ffmpeg` / `apt install ffmpeg` |
| **MIMO API Key** | `echo $MIMO_API_KEY` | 在 [xiaomimimo.com](https://xiaomimimo.com) 注册，然后 `export MIMO_API_KEY="sk-..."` |

不需要数据库，不需要其他后端服务。

## 部署

### 1. 克隆仓库

```bash
git clone https://github.com/Jedi-Pz/mimo-tts-proxy-openai.git
cd mimo-tts-proxy-openai
```

### 2. 创建虚拟环境并安装依赖

这个项目只有两个 Python 依赖：`openai`（OpenAI Python SDK，用作 MIMO 的 HTTP 客户端）和 `pyyaml`（配置文件解析）。

```bash
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install openai pyyaml
```

### 3. 设置 MIMO API Key

```bash
export MIMO_API_KEY="sk-你的-mimo-api-key"
```

确认一下：
```bash
echo $MIMO_API_KEY
```

代理启动时从环境变量读取 key，**不会**硬编码在任何文件里。

### 4. 查看配置文件

`config.yaml` 已经填了开箱即用的默认值：

```yaml
server:
  host: "127.0.0.1"    # 绑定地址（需要局域网访问时改为 0.0.0.0）
  port: 9880            # 端口

mimo:
  base_url: "https://api.xiaomimimo.com/v1"
  api_key_env: "MIMO_API_KEY"
  tts_model_preset: "mimo-v2.5-tts"              # 预置音色用的模型
  tts_model_clone: "mimo-v2.5-tts-voiceclone"    # 克隆音色用的模型
  audio_format: "wav"                             # MIMO 返回的格式

emotion:
  enabled: true                    # 设为 false 可以跳过 LLM 情绪推断
  model: "mimo-v2-flash"           # 做情绪推断的小而快的模型
  base_url: "https://api.xiaomimimo.com/v1"
  api_key_env: "MIMO_API_KEY"      # 如果没单独配就用 mimo 的 key
  max_input_chars: 1000            # 发给 LLM 的文本最大字符数

audio:
  default_format: "mp3"   # 客户端没指定 response_format 时用这个
  ffmpeg_path: "ffmpeg"   # ffmpeg 可执行文件路径
```

如果想让局域网内其他机器也能访问代理，把 `server.host` 改成 `0.0.0.0`。

### 5. 注册音色

编辑 `voices.yaml`。每个音色有四个字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `sample_file` | 克隆音色需要 | WAV 或 MP3 文件的绝对路径（≤ 10 MB）。代理会把它 base64 编码后以 `data:` URL 的形式传给 MIMO 做音色克隆。 |
| `preset` | 预置音色需要 | MIMO 预置音色名（如 `冰糖`、`alloy`）。不需要 `sample_file`，配这个就行。 |
| `base_style` | 否 | 一段固定的中文风格描述，始终拼在情绪提示前面（如 `温柔、知性的女声`）。 |
| `emotion_inference` | 否 | 布尔值。`true` 时，LLM 会读每条输入文字，动态追加一句情绪指导。 |

**克隆音色示例：**
```yaml
voices:
  zhuangfangyi:
    sample_file: "/home/you/voices/my-character.wav"
    base_style: "温柔、知性的女声"
    emotion_inference: true
```

**预置音色示例：**
```yaml
voices:
  bingtang:
    preset: "冰糖"
    base_style: "活泼少女"
    emotion_inference: false
```

**自动回退：** 任何不在 `voices.yaml` 里的音色名都会被当作 MIMO 预置音色直接使用——所以传 `"voice": "alloy"` 不用注册也能工作。

## 运行

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate

# 确保 key 已设置
export MIMO_API_KEY="sk-..."

# 启动代理
python -m mimo_tts_proxy.app
```

看到下面这行就说明启动成功了：
```
mimo-tts-proxy listening on http://127.0.0.1:9880/v1/audio/speech
```

**Linux 守护进程：** 用 `systemd`、`supervisord`，或者最简单的 `nohup python -m mimo_tts_proxy.app &`。

**macOS 守护进程：** 用 `launchd`，或者在 `tmux`/`screen` 会话里跑。

## 测试

### 单元测试（不需要 API Key）

```bash
python -m unittest discover -v tests/
```

预期结果：**18 个测试全部通过。**

### 冒烟测试（需要 MIMO_API_KEY）

这个脚本会启动代理，发两个真实 TTS 请求（一个克隆音色，一个预置音色），验证返回的音频有效，然后打印结果：

```bash
MIMO_API_KEY="sk-..." python smoke_test.py
```

预期输出：
```
server is up at http://127.0.0.1:9880
[clone ] 123456 bytes  audio/mpeg  -> /tmp/mimo_proxy_smoke_clone.mp3
[preset] 234567 bytes  audio/wav   -> /tmp/mimo_proxy_smoke_preset.wav

SMOKE TEST PASSED
```

## API 参考

### `GET /health`
返回 `{"status": "ok"}`，HTTP 200。

### `POST /v1/audio/speech`

完全兼容 OpenAI 协议。**请求头、请求体、返回格式都和 OpenAI TTS API 一致。**

#### 请求

```json
{
  "model": "tts-1",
  "input": "今天天气真好，我们一起出去玩吧！",
  "voice": "zhuangfangyi",
  "response_format": "mp3",
  "context": null
}
```

| 字段 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `model` | 否 | — | 代理忽略这个字段，保留是为了客户端兼容。 |
| `input` | **是** | — | 要合成语音的文本。上限约 4000 字符（MIMO 限制）。 |
| `voice` | **是** | — | 先在 `voices.yaml` 里查，找不到就当 MIMO 预置名用。 |
| `response_format` | 否 | `mp3` | 可选：`mp3`、`wav`、`opus`、`ogg`、`flac`、`aac`、`pcm`。 |
| `context` | 否 | `null` | **扩展字段。** 如果传了这个，就直接用作 MIMO 风格提示，完全跳过 base_style + 情绪推断。 |

#### 返回

**HTTP 200** — 音频字节流，附带正确的 `Content-Type` 头：
- `audio/mpeg`（mp3）
- `audio/wav`（wav）
- `audio/ogg`（opus/ogg）
- `audio/flac`（flac）
- `audio/aac`（aac）
- `audio/pcm`（pcm）

**HTTP 4xx / 5xx** — JSON 错误体：
```json
{
  "error": {
    "message": "voice is required",
    "type": "invalid_request_error"
  }
}
```

## 客户端配置

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="anything",            # 代理不校验，MIMO key 在服务端配好了
    base_url="http://127.0.0.1:9880/v1",  # ← 指向代理
)

with client.audio.speech.with_streaming_response.create(
    model="tts-1",
    input="你好世界",
    voice="zhuangfangyi",
    response_format="mp3",
) as response:
    response.stream_to_file("output.mp3")
```

### curl

```bash
curl -s -X POST http://127.0.0.1:9880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"你好世界","voice":"zhuangfangyi","response_format":"mp3"}' \
  -o output.mp3
```

### OpenClaw / Hermes

两个客户端都原生支持 OpenAI TTS 协议。把 TTS 的 `base_url` 配成 `http://127.0.0.1:9880/v1`，`api_key` 填任意非空字符串即可。

## 情绪推断

当音色配置了 `emotion_inference: true` 且 `config.yaml` 里 `emotion.enabled: true` 时，代理会把输入文本发给一个 LLM（默认 `mimo-v2-flash`），提示词如下：

```
你是语音合成情绪导演。阅读下面这段将要被朗读的文字，用一句简短的中文描述
该用什么语气和情绪来朗读（语调、语速、情绪色彩等）。只输出这一句描述，
不要朗读原文，不要解释。

文字：
<待朗读文本>
```

LLM 的回答（如 `语调上扬，带着惊喜和期待`）和音色的 `base_style` 用换行拼接后，作为 MIMO 的 `user` 消息——告诉 TTS 模型这段话该*怎么念*。

如果情绪推断失败（网络问题、LLM 返回空），代理会往 stderr 打一条警告，然后带着 `base_style` 继续。情绪推断的失败**不会**阻塞 TTS 请求。

要彻底关闭情绪推断，要么在 `config.yaml` 里设 `emotion.enabled: false`，要么把对应音色的 `emotion_inference` 设为 `false`。

## 音频格式与转码

MIMO 返回的永远是 WAV（`audio/wav`）。当客户端请求其他格式时，代理用 ffmpeg 转码：

| 目标格式 | ffmpeg 参数（除 `-i in.wav` 外） |
|---|---|
| `mp3` | `-acodec libmp3lame` |
| `opus` / `ogg` | `-acodec libopus -ac 1 -b:a 64k` |
| `flac` | `-acodec flac` |
| `aac` | `-acodec aac` |
| `pcm` | `-acodec pcm_s16le` |

如果客户端请求的格式和配置里 `audio_format` 一致（默认 `wav`），代理直接返回 MIMO 的原始 WAV——不经过 ffmpeg。

## 项目结构

```
mimo-tts-proxy-openai/
├── mimo_tts_proxy/         # Python 包
│   ├── __init__.py
│   ├── app.py              # 入口：组装依赖、启动服务器
│   ├── config.py           # YAML 配置 + 音色注册表加载
│   ├── emotion.py          # LLM 情绪推断 + 风格提示拼接
│   ├── mimo.py             # MIMO 请求构造 + 合成调用
│   ├── server.py           # HTTP 服务器（ThreadingHTTPServer）
│   ├── transcode.py        # 基于 ffmpeg 的音频格式转换
│   └── voices.py           # 音色解析（注册音色 → 克隆/预置）
├── tests/
│   ├── test_emotion.py     # 4 个测试 — assemble_style_prompt
│   ├── test_mimo.py        # 4 个测试 — select_model、build_mimo_request
│   ├── test_transcode.py   # 5 个测试 — content_type_for、needs_transcode
│   └── test_voices.py      # 3 个测试 — resolve_voice
├── config.yaml             # 服务器、MIMO、情绪推断、音频设置
├── voices.yaml             # 你的音色角色注册表
├── smoke_test.py           # 端到端测试（需要 MIMO_API_KEY）
├── .gitignore
├── README.md               # 本文件（中文）
└── README.en.md            # 英文版
```

## 常见问题

| 问题 | 可能原因 | 解决办法 |
|---|---|---|
| 启动时报 `MIMO API key not set` | 当前 shell 没 export `$MIMO_API_KEY` | 在同一个 shell 里 `export MIMO_API_KEY="sk-..."` |
| `voice sample >10MB` | 克隆样本文件太大 | 把 WAV 压缩/重采样到单声道 16-24 kHz |
| `unsupported sample format` | 克隆样本不是 `.wav` 或 `.mp3` | 转换：`ffmpeg -i file.m4a file.wav` |
| `ffmpeg failed` | ffmpeg 没安装或不在 PATH 里 | `brew install ffmpeg` / `apt install ffmpeg`，或在 `config.yaml` 里指定 `audio.ffmpeg_path` |
| stderr 出现 `emotion inference failed (continuing without)` | LLM 调用偶发失败 | 无害——TTS 仍然带着 `base_style` 正常工作 |
| `MIMO returned no audio data` | 音色名无效或 MIMO API 出错 | 检查预置名是否存在，或克隆样本是否有效；用 curl 直连 MIMO 排查 |
| Connection refused | 代理没启动，或 host/port 不对 | 检查 `config.yaml` 里的 `server.host` 和 `server.port`，确保端口没被占用 |

更多细节请看 [xiaomimimo.com](https://xiaomimimo.com) 的 MIMO API 文档。

## License

MIT
