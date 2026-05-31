# Usage Guide — All Providers

Per-provider setup and example commands for every supported model backend. The
[README](../../README.md#usage-closed-source-api-models) carries a condensed
version of this; the complete per-provider detail lives here.

See also: [Supported Models table](../../README.md#supported-models) ·
[Model Name Format](../../README.md#model-name-format).

---

## Usage: Closed-Source API Models

### Anthropic Claude

Get your API key at [console.anthropic.com](https://console.anthropic.com).

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Default model (claude-opus-4-6)
cheetahclaws

# Choose a specific model
cheetahclaws --model claude-sonnet-4-6
cheetahclaws --model claude-haiku-4-5-20251001

# Enable Extended Thinking
cheetahclaws --model claude-opus-4-6 --thinking --verbose
```

### OpenAI GPT

Get your API key at [platform.openai.com](https://platform.openai.com).

```bash
export OPENAI_API_KEY=sk-...

cheetahclaws --model gpt-4o
cheetahclaws --model gpt-4o-mini
cheetahclaws --model gpt-4.1-mini
cheetahclaws --model o3-mini
```

### Google Gemini

Get your API key at [aistudio.google.com](https://aistudio.google.com).

```bash
export GEMINI_API_KEY=AIza...

cheetahclaws --model gemini/gemini-3-flash-preview
cheetahclaws --model gemini/gemini-3.1-pro-preview
```

### Kimi (Moonshot AI)

Get your API key at [platform.moonshot.cn](https://platform.moonshot.cn).

```bash
export MOONSHOT_API_KEY=sk-...

cheetahclaws --model kimi/moonshot-v1-32k
cheetahclaws --model kimi/moonshot-v1-128k
```

### Qwen (Alibaba DashScope)

Get your API key at [dashscope.aliyun.com](https://dashscope.aliyun.com).

```bash
export DASHSCOPE_API_KEY=sk-...

cheetahclaws --model qwen/Qwen3.5-Plus
cheetahclaws --model qwen/Qwen3-MAX
cheetahclaws --model qwen/Qwen3.5-Flash
```

### Zhipu GLM

Get your API key at [open.bigmodel.cn](https://open.bigmodel.cn).

```bash
export ZHIPU_API_KEY=...

cheetahclaws --model zhipu/glm-4-plus
cheetahclaws --model zhipu/glm-4-flash   # free tier
```

### DeepSeek

Get your API key at [platform.deepseek.com](https://platform.deepseek.com).

```bash
export DEEPSEEK_API_KEY=sk-...

cheetahclaws --model deepseek/deepseek-chat
cheetahclaws --model deepseek/deepseek-reasoner
```

### MiniMax

Get your API key at [platform.minimaxi.chat](https://platform.minimaxi.chat).

```bash
export MINIMAX_API_KEY=...

cheetahclaws --model minimax/MiniMax-Text-01
cheetahclaws --model minimax/MiniMax-VL-01
cheetahclaws --model minimax/abab6.5s-chat
```

### LiteLLM (AWS Bedrock / Azure / Vertex AI)

Use the `litellm/` prefix when the upstream needs auth that's painful to
wire by hand — **AWS Bedrock SigV4 signing**, **Azure OpenAI deployment
routing**, or **Google Vertex AI service-account JWTs**. For plain
OpenAI-shaped endpoints (vLLM, LM Studio, TGI, Together, Groq, …) prefer
the zero-dependency `custom/` adapter from Option C below.

```bash
pip install ".[litellm]"

# AWS Bedrock — uses your boto3 credential chain (AWS_PROFILE, ~/.aws/
# credentials, IAM role on EC2). No explicit api_key needed.
export AWS_REGION=us-east-1
cheetahclaws --model litellm/bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0

# Azure OpenAI — deployment-id routing via api_base + api_version pair.
export AZURE_API_KEY=...
export AZURE_API_BASE=https://my-resource.openai.azure.com
export AZURE_API_VERSION=2024-10-01-preview
cheetahclaws --model litellm/azure/my-gpt4o-deployment

# Google Vertex AI — Application Default Credentials.
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export VERTEXAI_PROJECT=my-project
export VERTEXAI_LOCATION=us-central1
cheetahclaws --model litellm/vertex_ai/gemini-2.0-flash
```

The model string format is **`litellm/<provider>/<model>`** — the first
segment routes to this adapter, everything after is passed verbatim to
`litellm.completion(model=...)`. See [LiteLLM docs](https://docs.litellm.ai/docs/providers)
for the full list of 100+ supported providers, and
[`recipes.md`](recipes.md#alternative-cloud-providers-with-non-trivial-auth-via-the-litellm-provider)
for the troubleshooting table.

---

## Usage: Open-Source Models (Local)

### Option A — Ollama (Recommended)

Ollama runs models locally with zero configuration. No API key required.

**Step 1: Install Ollama**

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download
```

**Step 2: Pull a model**

```bash
# Best for coding (recommended)
ollama pull qwen2.5-coder          # 4.7 GB (7B)
ollama pull qwen2.5-coder:32b      # 19 GB (32B)

# General purpose
ollama pull llama3.3               # 42 GB (70B)
ollama pull llama3.2               # 2.0 GB (3B)

# Reasoning
ollama pull deepseek-r1            # 4.7 GB (7B)
ollama pull deepseek-r1:32b        # 19 GB (32B)

# Other
ollama pull phi4                   # 9.1 GB (14B)
ollama pull mistral                # 4.1 GB (7B)
```

**Step 3: Start Ollama server** (runs automatically on macOS; on Linux run manually)

```bash
ollama serve     # starts on http://localhost:11434
```

**Step 4: Run cheetahclaws**

```bash
cheetahclaws --model ollama/qwen2.5-coder
cheetahclaws --model ollama/llama3.3
cheetahclaws --model ollama/deepseek-r1
```

Or

```bash
python cheetahclaws.py --model ollama/qwen2.5-coder
python cheetahclaws.py --model ollama/llama3.3
python cheetahclaws.py --model ollama/deepseek-r1
python cheetahclaws.py --model ollama/qwen3.5:35b
```

**List your locally available models:**

```bash
ollama list
```

Then use any model from the list:

```bash
cheetahclaws --model ollama/<model-name>
```

---

### Option B — LM Studio

LM Studio provides a GUI to download and run models, with a built-in OpenAI-compatible server.

**Step 1:** Download [LM Studio](https://lmstudio.ai) and install it.

**Step 2:** Search and download a model inside LM Studio (GGUF format).

**Step 3:** Go to **Local Server** tab → click **Start Server** (default port: 1234).

**Step 4:**

```bash
cheetahclaws --model lmstudio/<model-name>
# e.g.:
cheetahclaws --model lmstudio/phi-4-GGUF
cheetahclaws --model lmstudio/qwen2.5-coder-7b
```

The model name should match what LM Studio shows in the server status bar.

---

### Option C — vLLM / Self-Hosted OpenAI-Compatible Server

For self-hosted inference servers (vLLM, TGI, llama.cpp server, etc.) that expose an OpenAI-compatible API:

Quick Start for option C:
Step 1: Start vllm:
 ```
CUDA_VISIBLE_DEVICES=7 python -m vllm.entrypoints.openai.api_server \
      --model Qwen/Qwen2.5-Coder-7B-Instruct \
      --host 0.0.0.0 \
      --port 8000 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes
```


 Step 2: Start cheetahclaws：
```
  export CUSTOM_BASE_URL=http://localhost:8000/v1
  export CUSTOM_API_KEY=none
  cheetahclaws --model custom/Qwen/Qwen2.5-Coder-7B-Instruct
```


```bash
# Example: vLLM serving Qwen2.5-Coder-32B
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-32B-Instruct \
    --port 8000 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes

# Then run cheetahclaws pointing to your server:
cheetahclaws
```

Inside the REPL:

```
/config custom_base_url=http://localhost:8000/v1
/config custom_api_key=token-abc123    # skip if no auth
/model custom/Qwen2.5-Coder-32B-Instruct
```

Or set via environment:

```bash
export CUSTOM_BASE_URL=http://localhost:8000/v1
export CUSTOM_API_KEY=token-abc123

cheetahclaws --model custom/Qwen2.5-Coder-32B-Instruct
```

For a remote GPU server:

```bash
/config custom_base_url=http://192.168.1.100:8000/v1
/model custom/your-model-name
```

#### Using vLLM with the Web UI

`--web --model <name>` now persists the model into `~/.cheetahclaws/config.json` before the server starts, so the Chat UI hits the right endpoint on the very first request:

```bash
export CUSTOM_BASE_URL=http://localhost:8000/v1
export CUSTOM_API_KEY=dummy            # vLLM doesn't validate but the OpenAI SDK requires non-empty
cheetahclaws --web --no-auth --port 8080 --model custom/qwen2.5-72b
```

If you skip `--model`, the Chat UI uses whatever was previously saved (it will **not** silently fall back to a default). Switch models on the fly from the Chat UI's Settings panel or with `/model custom/<name>` in the message box. The model name after `custom/` must match the vLLM `--served-model-name` exactly.
