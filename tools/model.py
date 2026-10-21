"""获取llm"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Python itself never reads a .env file -- without this, putting DEEPSEEK_API_KEY
# in .env has no effect and the call fails with "Missing credentials". Loading
# happens here rather than in an entry point so that both run_demo.py and
# main.py pick it up. load_dotenv() does not overwrite variables that are
# already set, so an exported key still takes precedence.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


def get_chat_gpt4o():
    return ChatOpenAI(
        model='gpt-4o',
        api_key=os.environ.get('OPENAI_API_KEY', ''),
        openai_api_base=os.environ.get('OPENAI_BASE_URL', ''),
        temperature=0.5
    )


def get_deepseek():
    return ChatOpenAI(
        model=os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
        openai_api_key=os.environ.get('DEEPSEEK_API_KEY', ''),
        openai_api_base=os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        # max_tokens=8192,
        temperature=0.5
    )


def access_model(prompts, model):
    m = ''
    if model == 'GPT-4o':
        m = get_chat_gpt4o()
    elif model == "deepseek":
        m = get_deepseek()

    resp = m.invoke(prompts).content
    return resp
