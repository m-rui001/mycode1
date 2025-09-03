from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import COORDINATOR_PROMPT
import json
import re
from app.utils.log_util import logger
from app.schemas.A2A import CoordinatorToModeler


class CoordinatorAgent(Agent):
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = COORDINATOR_PROMPT

    async def run(self, ques_all: str) -> CoordinatorToModeler:
        """用户输入问题 使用LLM 格式化 questions"""
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history({"role": "user", "content": ques_all})

        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )
        # 记录LLM原始响应，便于排查格式问题
        raw_content = response.choices[0].message.content
        logger.info(f"LLM原始响应内容: {raw_content}")
        json_str = raw_content


        json_match = re.search(r"```json(.*?)```", json_str, re.DOTALL)
        if json_match:
            # 提取代码块内的JSON
            json_str = json_match.group(1).strip()
        else:
            # 若没有代码块标记，直接使用原始内容尝试解析
            logger.warning("LLM返回内容未包含```json代码块，尝试直接解析JSON")
            json_str = json_str.strip()  # 仅去除首尾空白

        # 移除可能的控制字符
        json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)

        if not json_str:
            raise ValueError("提取后的JSON字符串为空，请检查输入内容。")

        try:
            questions = json.loads(json_str)
            # 验证必要字段存在性
            if "ques_count" not in questions:
                raise KeyError("JSON结构中缺少必要字段'ques_count'")
            ques_count = questions["ques_count"]
            # 验证字段类型
            if not isinstance(ques_count, int):
                raise TypeError(f"'ques_count'应为整数类型，实际为{type(ques_count).__name__}")
            
            logger.info(f"questions:{questions}")
            return CoordinatorToModeler(questions=questions, ques_count=ques_count)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误，原始字符串: {json_str}")
            logger.error(f"错误详情: {str(e)}")
            raise ValueError(f"JSON解析错误: {e}")
        except KeyError as e:
            logger.error(f"JSON结构错误: {e}")
            raise ValueError(f"JSON结构错误: {e}")
        except TypeError as e:
            logger.error(f"JSON字段类型错误: {e}")
            raise ValueError(f"JSON字段类型错误: {e}")