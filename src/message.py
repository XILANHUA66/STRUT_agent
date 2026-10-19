from dataclasses import dataclass
from enum import Enum
import json


class Message_type(Enum):
    user = "USER"
    system = "SYSREM"
    assistant = "ASSISTANT"
    other = "OTHER"

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
            "type": self.Message_type.value,
            "content":self.Message
        }

        return Message_dict

    # model返回直接变成信息体
    @classmethod
    def _modelrespence_to_mes(cls,jsonstr:str | None):
        
        message_type=Message_type("ASSISTANT")
        message=jsonstr
        
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
    