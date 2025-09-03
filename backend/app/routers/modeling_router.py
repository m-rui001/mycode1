from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from app.core.workflow import MathModelWorkFlow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.request import Problem
from app.schemas.response import SystemMessage
from app.utils.common_utils import (
    create_task_id,
    create_work_dir,
    get_current_files,
    md_2_docx,
)
import os
import asyncio
from fastapi import HTTPException
from icecream import ic
from app.schemas.request import ExampleRequest
from pydantic import BaseModel
import litellm
from app.config.setting import settings


router = APIRouter()


# 移除API配置相关的Pydantic模型，因为不再需要接收前端配置
# 移除ValidateApiKeyRequest、ValidateApiKeyResponse和SaveApiConfigRequest


# 移除保存API配置的接口，因为我们直接使用.env.dev中的配置
# @router.post("/save-api-config") 已移除


# 保留API验证接口，但默认使用.env.dev中的配置进行验证
@router.post("/validate-api-key")
async def validate_api_key():
    """
    验证 .env.dev 中配置的API Key有效性
    """
    try:
        # 使用.env.dev中的配置进行验证
        await litellm.acompletion(
            model=settings.COORDINATOR_MODEL,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            api_key=settings.COORDINATOR_API_KEY,
            base_url=settings.COORDINATOR_BASE_URL or None,
        )
        
        return {
            "valid": True,
            "message": "✓ 模型 API 验证成功（使用.env.dev配置）"
        }
    except Exception as e:
        error_msg = str(e)
        
        # 解析不同类型的错误
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {
                "valid": False,
                "message": "✗ API Key 无效或已过期（检查.env.dev配置）"
            }
        elif "404" in error_msg or "Not Found" in error_msg:
            return {
                "valid": False,
                "message": "✗ 模型 ID 不存在或 Base URL 错误（检查.env.dev配置）"
            }
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return {
                "valid": False,
                "message": "✗ 请求过于频繁，请稍后再试"
            }
        elif "403" in error_msg or "Forbidden" in error_msg:
            return {
                "valid": False,
                "message": "✗ API 权限不足或账户余额不足"
            }
        else:
            return {
                "valid": False,
                "message": f"✗ 验证失败: {error_msg[:50]}..."
            }


@router.post("/example")
async def exampleModeling(
    example_request: ExampleRequest,
    background_tasks: BackgroundTasks,
):
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)
    example_dir = os.path.join("app", "example", example_request.source)
    ic(example_dir)
    
    # 检查示例问题文件是否存在
    question_path = os.path.join(example_dir, "questions.txt")
    if not os.path.exists(question_path):
        raise HTTPException(status_code=404, detail=f"示例问题文件不存在: {question_path}")
    
    with open(question_path, "r", encoding="utf-8") as f:
        ques_all = f.read()

    # 复制示例数据文件
    current_files = get_current_files(example_dir, "data")
    for file in current_files:
        src_file = os.path.join(example_dir, file)
        dst_file = os.path.join(work_dir, file)
        with open(src_file, "rb") as src, open(dst_file, "wb") as dst:
            dst.write(src.read())
    
    # 存储任务ID
    await redis_manager.set(f"task_id:{task_id}", task_id)

    logger.info(f"Adding background task for task_id: {task_id}")
    # 将任务添加到后台执行
    background_tasks.add_task(
        run_modeling_task_async,
        task_id,
        ques_all,
        CompTemplate.CHINA,
        FormatOutPut.Markdown,
    )
    return {"task_id": task_id, "status": "processing"}


@router.post("/modeling")
async def modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),  # 从表单获取
    comp_template: CompTemplate = Form(...),  # 从表单获取
    format_output: FormatOutPut = Form(...),  # 从表单获取
    files: list[UploadFile] = File(default=None),
):
    # 验证.env.dev中的配置是否存在
    if not all([settings.COORDINATOR_API_KEY, settings.COORDINATOR_MODEL]):
        raise HTTPException(
            status_code=500, 
            detail="请先在.env.dev中配置API密钥和模型信息"
        )
    
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)

    # 保存上传的文件
    if files:
        logger.info(f"开始处理上传的文件，工作目录: {work_dir}")
        for file in files:
            try:
                data_file_path = os.path.join(work_dir, file.filename)
                logger.info(f"保存文件: {file.filename} -> {data_file_path}")

                if not file.filename:
                    logger.warning("跳过空文件名")
                    continue

                content = await file.read()
                if not content:
                    logger.warning(f"文件 {file.filename} 内容为空")
                    continue

                with open(data_file_path, "wb") as f:
                    f.write(content)
                logger.info(f"成功保存文件: {data_file_path}")

            except Exception as e:
                logger.error(f"保存文件 {file.filename} 失败: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"保存文件 {file.filename} 失败: {str(e)}"
                )
    else:
        logger.warning("没有上传文件")

    # 存储任务ID
    await redis_manager.set(f"task_id:{task_id}", task_id)

    logger.info(f"Adding background task for task_id: {task_id}")
    # 将任务添加到后台执行
    background_tasks.add_task(
        run_modeling_task_async, task_id, ques_all, comp_template, format_output
    )
    return {"task_id": task_id, "status": "processing"}


async def run_modeling_task_async(
    task_id: str,
    ques_all: str,
    comp_template: CompTemplate,
    format_output: FormatOutPut,
):
    logger.info(f"run modeling task for task_id: {task_id}")

    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=comp_template,
        format_output=format_output,
    )

    # 发送任务开始状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    # 短暂延迟确保WebSocket连接
    await asyncio.sleep(1)

    # 创建任务并等待完成
    task = asyncio.create_task(MathModelWorkFlow().execute(problem))
    # 设置超时时间（60分钟）
    try:
        await asyncio.wait_for(task, timeout=3600)
    except asyncio.TimeoutError:
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="任务处理超时", type="error"),
        )
        return

    # 发送任务完成状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务处理完成", type="success"),
    )
    # 转换md为docx
    md_2_docx(task_id)
