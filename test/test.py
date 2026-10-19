"""最小模型调用测试：单次输入 -> 单次输出。

使用 OpenAI 官方 SDK 调用 DeepSeek 的 OpenAI 兼容接口，不依赖任何其他框架。

运行（在项目根目录）：
    uv run python test/test.py
    uv run python test/test.py "自定义输入"

API Key 从项目根目录的 .env 读取：DEEPSEEK_API_KEY=sk-...
如需走其他兼容地址，可在 .env 中设置 DEEPSEEK_BASE_URL。
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_PROMPT = "用一句话解释什么是大语言模型。"
MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"


def main() -> None:
    load_dotenv()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.exit("未找到 DEEPSEEK_API_KEY，请在项目根目录的 .env 中配置。")

    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    message = response.choices[0].message

    print(f"输入: {prompt}")
    print(f"输出: {message.reasoning_content}")
    # print(f"推理过程: {getattr(message, 'reasoning_content', None)}")
    print(f"完整消息: {message}")


if __name__ == "__main__":
    main()
