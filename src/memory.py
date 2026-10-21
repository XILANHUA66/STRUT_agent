from src.message import Message,ToolcallMessage
import json

class _UnsetType:
    """用于区分“没传 content”和“显式传了 None”的哨兵类型。"""


_UNSET = _UnsetType()


class Memory():
    def __init__(self,system_prompt:str):
        self.memory=[]
        system_memory={
            "role":"system",
            "content":system_prompt
        }
        self.memory.append(system_memory)

    # add memory

    def _add_message_to_memory(self,message:Message):
        
        _dict={
            "role":message.get_type(),
            "content":message.get_content()
            }
        self.memory.append(_dict)

    def _add_toolcallMes_to_memory(
        self,
        mes: ToolcallMessage,
        ans: list[dict],
        content: str | None | _UnsetType = _UNSET,
        reasoning_content: str | None = None,
    ) -> None:
        """把一次工具调用及其执行结果按 API 协议写入记忆。

        写入的是两条（或多条）消息，而不是一条自定义结构：
          1. assistant：content + tool_calls
          2. 每个 tool_call 一条 tool：tool_call_id + 执行结果

        content 不传时使用 mes 自带的文本；显式传 None 表示
        assistant 消息只有 tool_calls、没有文本（这是合法的）。
        """
        calls = mes.toolcall or []
        if not calls:
            return

        if content is _UNSET:
            content = mes.get_content()

        self.memory.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": call.get("type", "function"),
                        "function": {
                            "name": call["name"],
                            "arguments": call["raw_arguments"],
                        },
                    }
                    for call in calls
                ],
            }
        )

        # use_Tool 返回的是 [{"id": ..., "success": ..., "result": ...}]
        results = {item["id"]: item.get("result", "") for item in ans or []}

        for call in calls:
            result = results.get(call["id"], "")
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)

            self.memory.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                }
            )

    # 传出 memory

    def get_all_memory_to_str(self)->str:

        return json.dumps(self.memory,ensure_ascii=False)
    
    def get_all_memory_to_dict(self)->list:

        return self.memory

    

    # 清空 memory
    def clear_memory(self):
        self.memory=[]