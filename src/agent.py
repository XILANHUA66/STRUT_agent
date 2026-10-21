import argparse
from typing import Any
from src.message import Message
from src.model import model
from src.memory import Memory
from src.tool import ToolRegistry,Tool,Tool_simplify,Tool_PtoM

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

    def _init_tool(self):
        # 这里添加
        _tools=[Tool_simplify(),Tool_PtoM()]
        self.tools=ToolRegistry(_tools)
    def run(self):
        step = 1
        conti_step = self.roll_step
        if_input=False
        self._init_tool()
        print("-"*35 + "agent启动" + "-"*35)
        
        while(step < self.max_step):
            if if_input or conti_step==0:
                str=input(">>>")
                if str=="exit":
                    break
                input_mes=Message._input_to_mes(str)
                self.memory._add_message_to_memory(input_mes)

            # print(self.memory.get_all_memory_to_str())
            #--------------
            next = False
            if next:
                break
            #-----------------
            output_mes=self.model.call(
                Message_info=self.memory.get_all_memory_to_dict(),
                tool=self.tools.get_form_openai()
                )
            _Message=output_mes[0]
            if output_mes[1]:
                _toolcallmes=output_mes[1]

                _toolcallmes.add_content(_Message)

                ans=self.tools.use_Tool(_toolcallmes)
                self.memory._add_toolcallMes_to_memory(_toolcallmes,ans)
                if_input=False    
                conti_step-=1
            # 判断
            else:
                self.memory._add_message_to_memory(_Message)
                if_input=True
                conti_step=self.roll_step
            
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


