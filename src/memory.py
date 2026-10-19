from .message import Message
import json

class Memory():
    
    memory:list[dict]

    def __init__(self,system_prompt:str):
        self.memory=[]
        system_memory={
            "type":"SYSTEM_PROMPT",
            "context":system_prompt
        }
        self.memory.append(system_memory)


    def _add_message_to_memory(self,message:Message):
        
        _dict={
            "type":Message.get_type,
            "content":Message.get_content
            }
        self.memory.append(_dict)

    def get_all_memory_to_str(self)->str:

        return json.dumps(self.memory)