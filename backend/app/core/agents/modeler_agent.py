from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import MODELER_PROMPT
from app.schemas.A2A import CoordinatorToModeler, ModelerToCoder
from app.utils.log_util import logger
import json
from icecream import ic

# TODO: 提问工具tool


import re  # 新增：导入re模块
import json
from typing import Any


# 假设以下是已定义的基础类和常量
class Agent:
    def __init__(self, task_id: str, model: Any, max_chat_turns: int):
        self.task_id = task_id
        self.model = model
        self.max_chat_turns = max_chat_turns
        self.chat_history = []
    
    async def append_chat_history(self, message: dict):
        self.chat_history.append(message)

class LLM:
    async def chat(self, history: list, agent_name: str) -> Any:
        # 模拟LLM聊天返回
        return type('obj', (object,), {'choices': [type('obj', (object,), {'message': {'content': '{}'}})]})

MODELER_PROMPT = "建模提示词"
CoordinatorToModeler = type('CoordinatorToModeler', (object,), {'questions': {}})
ModelerToCoder = type('ModelerToCoder', (object,), {'__init__': lambda self, questions_solution: setattr(self, 'questions_solution', questions_solution)})

class ModelerAgent(Agent):  # 继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 60,  # 添加最大对话轮次限制
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = MODELER_PROMPT

    async def run(self, coordinator_to_modeler: CoordinatorToModeler) -> ModelerToCoder:
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history(
            {
                "role": "user",
                "content": json.dumps(coordinator_to_modeler.questions),
            }
        )

        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )

        json_str = response.choices[0].message.content

        # 新增：使用正则提取JSON内容（替换原来的replace逻辑）
        match = re.search(r'```json(.*?)```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            # 尝试提取纯JSON（去除可能的前后缀）
            json_str = json_str.strip()

        if not json_str:
            raise ValueError("返回的 JSON 字符串为空，请检查输入内容。")
        try:
            questions_solution = json.loads(json_str)
            ic(questions_solution)
            return ModelerToCoder(questions_solution=questions_solution)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {e}")
