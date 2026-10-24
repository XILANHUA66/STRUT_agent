import argparse
from typing import Any
from src.message import Message
from src.model import model
from src.memory import Memory
from src.tool import (
    ToolRegistry,
    Tool,
    simplify,
    prompt_to_model,
    )

input_path="D:\agent_learn_to_work\newagent-main\\cline_com"
case_path="D:\\agent_learn_to_work\\newagent-main\\cline_com"
class Agent:
    def __init__(
            self,
            model_name:str,

            prompt_templates:str,

            roll_step:int,

            max_step:int,
    ):
        # 实例化
        self.model=model(model_name=model_name)
        self.prompt_templates=prompt_templates
        self.memory=Memory(prompt_templates)
        self.max_step=max_step
        self.roll_step=roll_step
        self._init_tool()

    def _init_tool(self):
        # 这里添加工具类
        _tools=[Tool.Tool_building(simplify),Tool.Tool_building(prompt_to_model)]

        self.tools=ToolRegistry(_tools)

    def run(self):
        
        step = 1
        
        # 控制输入
        conti_step = 0
        if_input=False
        
        print("-"*35 + "agent启动" + "-"*35)
        
        while(step < self.max_step):
            # 输入
            if if_input or conti_step==self.roll_step:
                str=input(">>>")
                print("\n")
                if str=="exit":
                    break
                input_mes=Message._input_to_mes(str)
                self.memory._add_mes_to_memory(input_mes)

            # call_deepseek
            output_mes=self.model.call(
                Message_info=self.memory.get_all_memory_to_dict(),
                tool=self.tools.get_form_openai()
                )

            # 判断output是否有tool_call
            _Message=output_mes[0]
            if output_mes[1]:
                _toolcallmes=output_mes[1]
                ans=self.tools.use_Tool(_toolcallmes)
                self.memory._add_toolcallMes_to_memory(_toolcallmes,ans)
                if_input=False    
                conti_step+=1

                print("-"*35 + f"contiune step {conti_step}..." + "-"*35)
            else:
                self.memory._add_mes_to_memory(_Message)
                if_input=True
                conti_step=0

            
            print(_Message.get_content())
            step+=1

        
        print("-"*35+"对话结束"+"-"*35)
        print(self.memory.get_all_memory_to_str())


            

def main():
    model_name="deepseek-flash"
    prompt="你是一个ai帮手,负责帮助我复现STCUT论文,请等待我的指令或输入。开始时先介绍下自己"
    agent=Agent(model_name=model_name,roll_step=10,prompt_templates=prompt,max_step=10)
    agent.run()

if __name__=="__main__":
    main()


