#!/usr/bin/env python3
"""
Codex 本地推理封装 — Ollama 接入层
支持本地模型推理，当 DeepSeek API 不可用时作为降级方案

用法:
    python3 codex/ollama_inference.py --model tinyllama --prompt "Hello"
    python3 codex/ollama_inference.py --list          # 列出可用模型
    python3 codex/ollama_inference.py --health        # 健康检查

环境变量:
    OLLAMA_HOST - Ollama 服务地址 (默认: http://127.0.0.1:11434)
"""
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", "qwen2.5:0.5b-instruct-q4_0")


def _post(endpoint, data):
    """发送 POST 请求到 Ollama API"""
    url = f"{DEFAULT_HOST}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": str(e), "available": False}


def _get(endpoint):
    """发送 GET 请求"""
    url = f"{DEFAULT_HOST}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": str(e), "available": False}


def health_check():
    """检查 Ollama 服务是否可用"""
    result = _get("/api/tags")
    if result.get("error"):
        return {
            "available": False,
            "error": result["error"],
            "host": DEFAULT_HOST,
        }
    models = result.get("models", [])
    return {
        "available": True,
        "host": DEFAULT_HOST,
        "model_count": len(models),
        "models": [m.get("name", "") for m in models],
    }


def list_models():
    """列出本地可用模型"""
    result = _get("/api/tags")
    if result.get("error"):
        return []
    return [
        {
            "name": m.get("name", ""),
            "size_mb": round(m.get("size", 0) / 1024 / 1024, 1),
            "modified": m.get("modified_at", "")[:10],
        }
        for m in result.get("models", [])
    ]


def generate(prompt, model=None, system=None, max_tokens=512):
    """
    生成文本（非流式）

    Args:
        prompt: 用户提示
        model: 模型名称（默认 tinyllama）
        system: 系统提示
        max_tokens: 最大生成 token 数

    Returns:
        dict with response, model, duration_ms, etc.
    """
    model = model or DEFAULT_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7,
        },
    }
    if system:
        payload["system"] = system

    result = _post("/api/generate", payload)
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
            "model": model,
        }

    return {
        "success": True,
        "model": model,
        "response": result.get("response", ""),
        "total_duration_ms": result.get("total_duration", 0) // 1_000_000,
        "load_duration_ms": result.get("load_duration", 0) // 1_000_000,
        "prompt_eval_count": result.get("prompt_eval_count", 0),
        "eval_count": result.get("eval_count", 0),
        "done": result.get("done", False),
    }


def chat(messages, model=None, max_tokens=512):
    """
    对话模式

    Args:
        messages: [{"role": "system"/"user"/"assistant", "content": "..."}]
        model: 模型名称
        max_tokens: 最大生成 token 数

    Returns:
        dict with response, model, etc.
    """
    model = model or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7,
        },
    }

    result = _post("/api/chat", payload)
    if result.get("error"):
        return {
            "success": False,
            "error": result["error"],
            "model": model,
        }

    msg = result.get("message", {})
    return {
        "success": True,
        "model": model,
        "response": msg.get("content", ""),
        "role": msg.get("role", "assistant"),
        "total_duration_ms": result.get("total_duration", 0) // 1_000_000,
        "prompt_eval_count": result.get("prompt_eval_count", 0),
        "eval_count": result.get("eval_count", 0),
    }


def summarize_market_analysis(data, model=None):
    """
    市场分析摘要（本地推理版，降级方案）

    Args:
        data: 市场数据字典

    Returns:
        摘要文本
    """
    fg = data.get("fg", {})
    debate = data.get("debate", {})
    positions = data.get("positions", {}).get("positions", [])

    prompt = f"""请用中文简要分析当前加密市场状态：

恐惧贪婪指数: {fg.get('value', 50)} ({fg.get('classification', 'Neutral')})
AI 多空决策: {debate.get('decision', 'HOLD')} (信心 {debate.get('confidence', 0)}%)
持仓数: {len(positions)}
市场制度: {data.get('regime', 'unknown')}

用3句话总结：1) 当前市场状态 2) 风险提示 3) 操作建议。
"""

    result = generate(
        prompt,
        model=model,
        system="你是一个专业的加密货币分析师，回答简洁准确。",
        max_tokens=300,
    )

    if result["success"]:
        return result["response"].strip()
    else:
        return f"[本地推理不可用: {result.get('error', 'unknown')}]"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Codex 本地推理 (Ollama)")
    parser.add_argument("--health", action="store_true", help="健康检查")
    parser.add_argument("--list", action="store_true", help="列出模型")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--prompt", default=None, help="提示文本")
    parser.add_argument("--max-tokens", type=int, default=512, help="最大token数")
    args = parser.parse_args()

    if args.health:
        hc = health_check()
        print(json.dumps(hc, indent=2, ensure_ascii=False))
        return 0 if hc["available"] else 1

    if args.list:
        models = list_models()
        if not models:
            print("无可用模型")
        else:
            for m in models:
                print(f"  {m['name']}  ({m['size_mb']} MB)")
        return 0

    if args.prompt:
        result = generate(args.prompt, model=args.model, max_tokens=args.max_tokens)
        if result["success"]:
            print(result["response"])
            print(f"\n[模型: {result['model']} | 耗时: {result['total_duration_ms']}ms | {result['eval_count']} tokens]")
        else:
            print(f"❌ 推理失败: {result.get('error')}")
            return 1
        return 0

    # 默认：健康检查
    hc = health_check()
    status = "✅ 可用" if hc["available"] else "❌ 不可用"
    print(f"Ollama 服务: {status}")
    print(f"地址: {hc.get('host', 'N/A')}")
    if hc.get("model_count"):
        print(f"本地模型: {hc['model_count']} 个")
        for m in hc.get("models", []):
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
