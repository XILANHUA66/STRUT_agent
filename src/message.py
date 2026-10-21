from dataclasses import dataclass
from enum import Enum
import json
from openai.types.chat import ChatCompletionMessageToolCall

class Message_type(Enum):
    user = "user"
    system = "system"
    assistant = "assistant"
    other = "other"
    toolcall="toolcall"

@dataclass
class Message():
    Message_type:Message_type
    Message:str | None

    def _check_empty(self)-> bool:
        return False

    def _to_dict(self)->dict:
        if self._check_empty:
            pass 

        Message_dict={
            "role": self.Message_type.value,
            "content":self.Message
        }

        return Message_dict

    # model返回直接变成信息体
    @classmethod
    def _modelrespence_to_mes(cls,jsonstr:str | None):
        
        message_type=Message_type("assistant")
        message=jsonstr
        
        return cls(message_type,message)

    @classmethod
    def _input_to_mes(cls,input:str | None):
        message_type=Message_type("user")
        message=input
        return cls(message_type,message)

    # 返回信息类型
    def get_type(self)->str:
        return self.Message_type.value


    # 返回信息内容
    def get_content(self)->str:

        if self.Message != None:
            return self.Message
        else:
            return "no thing!"


class ToolcallMessage(Message):
    toolcall:list[dict]
    def __init__(self, Message_type,Message,toolcall:list[dict]):
        super().__init__(Message_type,Message)
        self.toolcall=toolcall

    @classmethod
    def _toolcall_to_mas(cls,toolcalls: list[ChatCompletionMessageToolCall] | None):
        parsed: list[dict] = []
        if toolcalls==None:
            return None
        for tc in toolcalls or []:
            raw_arguments = tc.function.arguments
            try:
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"工具 {tc.function.name} 的参数不是合法 JSON: {raw_arguments!r}"
                ) from exc
        
            parsed.append(
                {
                "id": tc.id,
                "type": tc.type,
                "name": tc.function.name,
                "arguments": arguments,
                "raw_arguments": raw_arguments,
                }
            )
        # print(parsed)
        return cls("toolcall"," ",parsed)

    def add_content(self, Mes:Message):
        self.Message=Mes.get_content() 
