import json
import os

import tools.main as toolmain
from dataclasses import dataclass
from typing import Any, Callable
from src.message import ToolcallMessage
from src.model import model
from src.paths import ensure_output_dir
from openai.types.chat import ChatCompletionMessageToolCall


@dataclass
class Tool:
    name: str
    description: str | None
    parameters: dict
    execute: Callable[..., Any]

    def transform_to_openai(self):
        _dict={
        "type": "function",
        "function": {
            "name": self.name,
            "description": self.description,
            "parameters":self.parameters ,
            "strict":True
            }
        }
        
        return _dict
    
    def using(self, parameters: dict) -> Any:
        """用模型给出的参数执行工具。

        parameters 来自 tool_call 的 arguments。模型返回的原始值是 JSON
        字符串，已经在 ToolcallMessage._toolcall_to_mas 里 json.loads 成 dict，
        这里直接用 ** 展开成关键字参数传给 execute。
        """
        if not isinstance(parameters, dict):
            raise TypeError(
                f"工具 {self.name} 的参数必须是 dict，"
                f"收到 {type(parameters).__name__}"
            )

        return self.execute(**parameters)



class ToolRegistry:
    def __init__ (self , tools:list[Tool] | None = None ):
        self.tools:dict[str,Tool]={}
        for i in tools or []:
            self.register(i)

    def register(self, t:Tool)->None:
        self.tools[t.name]=t

    def get(self,name:str)->Tool:
        return self.tools[name]

    def get_form_openai(self):
        return [tool.transform_to_openai() for tool in self.tools.values()]

    def use_Tool(self,ToolcallMes:ToolcallMessage)->list[dict]:
        _dict_toolcall=ToolcallMes.toolcall
        ans_totall:list[dict]=[]
        if _dict_toolcall is not None:
            for i in _dict_toolcall:
                id=i["id"]
                name=i["name"]
                arguments=i["arguments"]

                func=self.get(name)

                ans=func.using(parameters=arguments)
                if ans!=" ":
                    ans_totall.append({
                        "id":id,
                        "success":"True",
                        "result":ans
                    })
                else:
                    ans_totall.append({
                        "id":id,
                        "success":"False",
                        "result":ans
                    })
        return ans_totall




class STRUT_simlify(Tool):
    """
    根据input_path上传的c语言文件和case_path的样例文件，进行第一步处理，生成{上下文，用例}的提示词
    """
    input_path:str
    output_path:str
    case_path:str
    def __init__(self,input_path,case_path,output_path=None):
        super.__init__
        self.input_path=input_path
        self.case_path=case_path

        if output_path is None:
            # 默认写入 cline_com/output/，避免覆盖原文件
            output_path=os.path.join(
                ensure_output_dir(), os.path.basename(input_path)
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.output_path=output_path


    def simplify(self):
        toolmain.simplify(input_path=self.input_path, output_path=self.output_path)
        function = toolmain.get_file(self.output_path)
        return function
    
    def case_parse(self):
        case_content = toolmain.get_file(self.case_path)
        case, default_PTR, has_stub = toolmain.case_generator(case_content)
        return case, default_PTR, has_stub

    # 构建获取提示词:调用
    def prompt_building(self):

        function=self.simplify()
        case, default_PTR, has_stub=self.case_parse()
        prompt = toolmain.prompt_generator(function, case, has_stub)

        # 把提示词保存到 cline_com/output/prompt.txt
        prompt_path = os.path.join(ensure_output_dir(), "prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        return prompt,default_PTR

def simplify( input_path,case_path,output_path=None)->str:
    """
    根据 input_path 的 C 文件和 case_path 的样例文件，生成测试用例提示词。

    处理过程：
    1. 简化 C 代码：删除无函数体的声明、删除全局变量赋值等；
    2. 简化后的程序保存到 output_path，原始文件不会被修改；
    3. 结合样例用例生成 prompt。

    参数：
    - input_path：被测 C 文件路径，默认为
      'D:\\agent_learn_to_work\\newagent-main\\cline_com\\input\\circle.c'
    - case_path：样例用例 JSON 路径，默认为
      'D:\\agent_learn_to_work\\newagent-main\\cline_com\\input\\circle_seed.json'
    - output_path：简化后文件的保存路径，默认保存到
      'D:\\agent_learn_to_work\\newagent-main\\cline_com\\output/<原文件名>'，并自动创建目录。
    提示词同时保存到 'D:\\agent_learn_to_work\\newagent-main\\cline_com\\output\\prompt.txt'。

    返回 JSON 字符串：
    - 成功：{"success": true, "prompt": "...", "PTR": [...]}
    - 失败：{"success": false, "error": "...", "message": "..."}
    """
    try:
        strut=STRUT_simlify(input_path,case_path,output_path)
        prompt,PTR=strut.prompt_building()
        ans={
            "success":True,
            "prompt":prompt,
            "PTR":PTR,
        }
        return json.dumps(ans,ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {
                "success":False,
                "error":type(e).__name__,
                "message":str(e),
            },
            ensure_ascii=False,
        )

def Tool_simplify():
    strut=Tool(
        name="Tool_simplify",
        description=simplify.__doc__,
        execute=simplify,
        parameters={
        "type": "object",
        "properties": {
            "input_path": {"type": "string"},
            "case_path": {"type": "string"},
            "output_path": {
                "type": ["string", "null"]
            },
        },
        "required": [
            "input_path",
            "case_path",
            "output_path",
        ],
        "additionalProperties": False,
        },
    )
    return strut


def prompt_to_model(input_prompt:str):
    """
    这一步是发送prompt到无/新记忆体的model，保存并然后获得输出
    """
    try:
        mod=model("deepseek-flash")
        res=mod.tool_call(input_prompt)
        return json.dumps({
                "success":True,
                "response":res,
        },ensure_ascii=False)
    except:
        return json.dumps({
            "success":False,
            "response":"something woring"
        },ensure_ascii=False)

def Tool_PtoM():
    strut=Tool(
        name="prompt_to_model",
        description=prompt_to_model.__doc__,
        execute=prompt_to_model,
        parameters={
        "type": "object",
        "properties": {
            "input_prompt": {"type": "string"},
        },
        "required": [
            "input_prompt"
        ],
        "additionalProperties": False,
        },
    )
    return strut


