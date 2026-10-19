import argparse
from typing import Any
from message import Message

class agent:
    def __init__(
            self,
            model,
            tools:list[ Any],
            prompt_templates:str,
            memory,
            manage_models,
            max_step:int=20
    ):
        self.model=model
        self.tools=tools
        self.prompt_templates=prompt_templates
        self.memory=memory
        self.manage_models=manage_models
        self.max_step=max_step

        self.memory.append_system(self.prompt_templates[])

    def run(self):
        step = 0
        finally_step = False
        while(step < self.max_step and not finally_step):
            pass

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument(
        "--model",
        type=str,
        help="add model name"
    )
    arg.add_argument(
        "--apiKey",
        type=str,
        help="modelapikey"
    )


