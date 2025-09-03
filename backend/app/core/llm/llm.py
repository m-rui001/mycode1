import json
from app.utils.common_utils import transform_link, split_footnotes
from app.utils.log_util import logger
import time
from app.schemas.response import (
    CoderMessage,
    WriterMessage,
    ModelerMessage,
    SystemMessage,
    CoordinatorMessage,
)
from app.services.redis_manager import redis_manager
from litellm import acompletion
import litellm
from litellm.exceptions import (
    AuthenticationError,
    NotFoundError,
    InvalidRequestError,
    RateLimitError,
    InternalServerError
)
from app.schemas.enums import AgentType
from app.utils.track import agent_metrics
from icecream import ic

litellm.callbacks = [agent_metrics]


class LLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        task_id: str,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.chat_count = 0
        self.max_tokens: int | None = None  # 最大token数限制
        self.task_id = task_id

    async def chat(
        self,
        history: list = None,
        tools: list = None,
        tool_choice: str = None,
        max_retries: int = 8,
        retry_delay: float = 1.0,
        top_p: float | None = None,
        agent_name: AgentType = AgentType.SYSTEM,
        sub_title: str | None = None,
    ):
        logger.info(f"subtitle是:{sub_title}")

        # 验证和修复工具调用完整性
        if history:
            history = self._validate_and_fix_tool_calls(history)

        kwargs = {
            "api_key": self.api_key,
            "model": self.model,
            "messages": history,
            "stream": False,
            "top_p": top_p,
            "metadata": {"agent_name": agent_name},
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        if self.base_url:
            kwargs["base_url"] = self.base_url

        for attempt in range(max_retries):
            try:
                response = await acompletion(**kwargs)
                logger.info(f"API返回: {response}")
                if not response or not hasattr(response, "choices"):
                    raise ValueError("无效的API响应")
                self.chat_count += 1
                await self.send_message(response, agent_name, sub_title)
                return response
            except AuthenticationError as e:
                error_msg = f"API Key无效或已过期: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )
            except NotFoundError as e:
                error_msg = f"模型不存在（Model ID错误）: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )
            except InvalidRequestError as e:
                error_msg = f"请求参数错误（如Base URL无效）: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )
            except RateLimitError as e:
                error_msg = f"速率限制超限，请稍后重试: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )
            except (json.JSONDecodeError, InternalServerError) as e:
                error_msg = f"服务端错误: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )
            except Exception as e:
                error_msg = f"未知错误: {str(e)[:50]}"
                logger.error(f"第{attempt + 1}次重试: {error_msg}")
                await self.send_message(
                    SystemMessage(content=error_msg, type="error"),
                    agent_name,
                    sub_title
                )

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            logger.debug(f"请求参数: {kwargs}")
            raise

    def _validate_and_fix_tool_calls(self, history: list) -> list:
        """验证并修复工具调用完整性"""
        if not history:
            return history

        ic(f"🔍 开始验证工具调用，历史消息数量: {len(history)}")

        fixed_history = []
        i = 0

        while i < len(history):
            msg = history[i]

            if isinstance(msg, dict) and "tool_calls" in msg and msg["tool_calls"]:
                ic(f"📞 发现tool_calls消息在位置 {i}")

                valid_tool_calls = []
                invalid_tool_calls = []

                for tool_call in msg["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    ic(f"  检查tool_call_id: {tool_call_id}")

                    if tool_call_id:
                        found_response = False
                        for j in range(i + 1, len(history)):
                            if (
                                history[j].get("role") == "tool"
                                and history[j].get("tool_call_id") == tool_call_id
                            ):
                                ic(f"  ✅ 找到匹配响应在位置 {j}")
                                found_response = True
                                break

                        if found_response:
                            valid_tool_calls.append(tool_call)
                        else:
                            ic(f"  ❌ 未找到匹配响应: {tool_call_id}")
                            invalid_tool_calls.append(tool_call)

                if valid_tool_calls:
                    fixed_msg = msg.copy()
                    fixed_msg["tool_calls"] = valid_tool_calls
                    fixed_history.append(fixed_msg)
                    ic(
                        f"  🔧 保留 {len(valid_tool_calls)} 个有效tool_calls，移除 {len(invalid_tool_calls)} 个无效的"
                    )
                else:
                    cleaned_msg = {k: v for k, v in msg.items() if k != "tool_calls"}
                    if cleaned_msg.get("content"):
                        fixed_history.append(cleaned_msg)
                        ic(f"  🔧 移除所有tool_calls，保留消息内容")
                    else:
                        ic(f"  🗑️ 完全移除空的tool_calls消息")

            elif isinstance(msg, dict) and msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id")
                ic(f"🔧 检查tool响应消息: {tool_call_id}")

                found_call = False
                for j in range(len(fixed_history)):
                    if fixed_history[j].get("tool_calls") and any(
                        tc.get("id") == tool_call_id
                        for tc in fixed_history[j]["tool_calls"]
                    ):
                        found_call = True
                        break

                if found_call:
                    fixed_history.append(msg)
                    ic(f"  ✅ 保留有效的tool响应")
                else:
                    ic(f"  🗑️ 移除孤立的tool响应: {tool_call_id}")

            else:
                fixed_history.append(msg)

            i += 1

        if len(fixed_history) != len(history):
            ic(f"🔧 修复完成: {len(history)} -> {len(fixed_history)} 条消息")
        else:
            ic(f"✅ 验证通过，无需修复")

        return fixed_history

    async def send_message(self, response, agent_name: AgentType, sub_title: str | None = None):
        """修复：明确区分系统消息和正常响应，确保类型安全"""
        logger.info(f"subtitle是:{sub_title}")
        
        # 处理系统错误消息
        if isinstance(response, SystemMessage):
            agent_msg = response
        else:
            # 处理正常响应
            content = response.choices[0].message.content
            
            # 根据Agent类型生成对应消息
            if agent_name == AgentType.CODER:
                agent_msg = CoderMessage(content=content)
            elif agent_name == AgentType.WRITER:
                content, _ = split_footnotes(content)
                content = transform_link(self.task_id, content)
                agent_msg = WriterMessage(
                    content=content,
                    sub_title=sub_title,
                )
            elif agent_name == AgentType.MODELER:
                agent_msg = ModelerMessage(content=content)
            elif agent_name == AgentType.SYSTEM:
                agent_msg = SystemMessage(content=content)
            elif agent_name == AgentType.COORDINATOR:
                agent_msg = CoordinatorMessage(content=content)
            else:
                raise ValueError(f"不支持的agent类型: {agent_name}")

        # 发送消息到Redis
        await redis_manager.publish_message(
            self.task_id,
            agent_msg,
        )


async def simple_chat(model: LLM, history: list) -> str:
    """简化版聊天函数"""
    kwargs = {
        "api_key": model.api_key,
        "model": model.model,
        "messages": history,
        "stream": False,
    }

    if model.base_url:
        kwargs["base_url"] = model.base_url

    response = await acompletion(**kwargs)
    return response.choices[0].message.content
