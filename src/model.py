import json
import os
import openai
from dotenv import load_dotenv
from src.message import Message,ToolcallMessage
from src.paths import OUTPUT_DIR
from typing import Any

class model:
    model_name:str
    def __init__(self,model_name:str):
        self.model_name=model_name
        load_dotenv()
        api_key=os.environ.get("DEEPSEEK_API_KEY")
        base_url=os.environ.get("DEEPSEEK_BASE_URL")

        self.cline = openai.OpenAI(api_key=api_key,base_url=base_url)
        
    def call(self, Message_info,tool)->list[Message | ToolcallMessage |None]:

        response=self.cline.chat.completions.create(
            model=self.model_name,
            tools=tool,
            messages=Message_info
        )
        response=response.choices[0].message

        Mes=Message._modelrespence_to_mes(response.content)
        
        toolmes=None
        if response.tool_calls !=None:
            toolmes=ToolcallMessage._toolcall_to_mas(response.tool_calls)
            toolmes.add_content(Mes=Mes)
        return [Mes,toolmes]

    def tool_call(self,prompt:str,output_path:str=os.path.join(OUTPUT_DIR,"result.json")):
        response=self.cline.chat.completions.create(
            model=self.model_name,
            messages=[{
                "role":"user",
                "content":prompt
                }]
        )
        result=response.choices[0].message.content

        # 保存到 output/result.json（目录不存在时自动创建）
        os.makedirs(os.path.dirname(os.path.abspath(output_path)),exist_ok=True)
        with open(output_path,"w",encoding="utf-8") as f:
            json.dump({
                "model":self.model_name,
                "response":result,
            },f,ensure_ascii=False,indent=2)
        print(result)

        return result
                


