
import os
import openai
from dotenv import load_dotenv
from .message import Message


class model:
    model_name:str
    def __init__(self):
        load_dotenv()
        api_key=os.environ.get("DEEPSEEK_API_KEY")
        base_url=os.environ.get("DEEPSEEK_BASE_URL")

        self.cline = openai.OpenAI(api_key=api_key,base_url=base_url)
        
    def call(self, Message_info)->Message:
        response=self.cline.chat.completions.create(
            model=self.model_name,
            messages=Message_info
        )
        return Message._modelrespence_to_mes(response.choices[0].message.content)


