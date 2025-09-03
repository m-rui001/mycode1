from app.models.user_output import UserOutput
from app.tools.base_interpreter import BaseCodeInterpreter
from app.core.agents.modeler_agent import ModelerToCoder
from typing import Dict, List, Union


class Flows:
    def __init__(self, questions: Dict[str, Union[str, int]]):
        self.flows: Dict[str, Dict] = {}
        self.questions: Dict[str, Union[str, int]] = questions  # 保持原始类型定义

    def set_flows(self, ques_count: int) -> None:
        """初始化流程结构，保持原始逻辑不变"""
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
        ]
        self.flows = {key: {} for key in seq}  # 维持原始空字典初始化

    def get_solution_flows(
        self, 
        questions: Dict[str, Union[str, int]], 
        modeler_response: ModelerToCoder,
        code_interpreter: BaseCodeInterpreter  # 新增：用于获取数据集列表，解决TODO问题
    ) -> Dict[str, Dict[str, str]]:
        """修正：补充数据集获取逻辑，修复参数依赖问题"""
        # 筛选ques相关配置（保持原始筛选逻辑）
        questions_quesx = {
            key: value
            for key, value in questions.items()
            if key.startswith("ques") and key != "ques_count"
        }

        # 构建ques类流程（保持原始结构）
        ques_flow = {
            key: {
                "coder_prompt": f"""
                    参考建模手给出的解决方案：{modeler_response.questions_solution[key]}
                    完成如下问题要求：{value}
                    注意：需输出完整可执行代码，包含数据加载、模型实现、结果输出步骤
                """,
            }
            for key, value in questions_quesx.items()
        }

        # 修正EDA流程：替换TODO，通过code_interpreter获取实际数据集
        eda_files = code_interpreter.list_files()  # 获取当前目录所有文件
        eda_data_info = ", ".join([f"'{f}'" for f in eda_files if f.endswith(('.csv', '.xlsx', '.txt'))])  # 筛选数据文件

        flows = {
            "eda": {
                "coder_prompt": f"""
                    参考建模手给出的解决方案：{modeler_response.questions_solution["eda"]}
                    对当前目录下的数据集（{eda_data_info}）执行以下操作：
                    1. 数据清洗：处理缺失值（用均值/中位数填充）、异常值（3σ法则剔除）、重复值
                    2. 描述性统计：计算均值、方差、极值、相关性系数并输出
                    3. 可视化：绘制变量分布直方图、相关性热力图
                    4. 结果保存：清洗后的数据保存为'cleaned_data.csv'到当前目录
                    注意：不需要复杂模型，仅需数据预处理与可视化代码
                """,
            },
            **ques_flow,
            "sensitivity_analysis": {
                "coder_prompt": f"""
                    参考建模手给出的解决方案：{modeler_response.questions_solution["sensitivity_analysis"]}
                    完成敏感性分析：
                    1. 基于已构建模型，选择核心参数进行变动测试
                    2. 输出参数变动幅度与结果指标的对应表格
                    3. 绘制灵敏度曲线（横轴：参数变动幅度，纵轴：结果变化率）
                    4. 给出鲁棒性结论
                """,
            },
        }
        return flows

    def get_write_flows(
        self, 
        user_output: UserOutput, 
        config_template: Dict[str, str], 
        bg_ques_all: str
    ) -> Dict[str, str]:
        """修正：确保模型求解信息转为字符串，避免类型拼接错误"""
        # 获取模型构建与求解信息，转为字符串防止非字符串类型拼接问题
        model_build_solve = str(user_output.get_model_build_solve())

        flows = {
            "firstPage": f"""问题背景：{bg_ques_all}
                不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["firstPage"]}
                要求：包含标题、摘要、关键词，严格匹配模板结构""",
            
            "RepeatQues": f"""问题背景：{bg_ques_all}
                不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["RepeatQues"]}
                要求：包含问题背景（带数据支撑）、问题重述（分点明确）""",
            
            "analysisQues": f"""问题背景：{bg_ques_all}
                不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["analysisQues"]}
                要求：每个问题分析含需求拆解、模型适配对比，逻辑递进清晰""",
            
            "modelAssumption": f"""问题背景：{bg_ques_all}
                不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["modelAssumption"]}
                要求：覆盖数据、约束、资源、需求四类假设，含合理性依据""",
            
            "symbol": f"""不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["symbol"]}
                要求：符号、含义、单位对应清晰，与模型公式一致""",
            
            "judge": f"""不需要编写代码，根据模型的求解信息：{model_build_solve}
                按照如下模板撰写：{config_template["judge"]}
                要求：优点含国赛评分点、缺点客观、改进推广具体可行"""
        }
        return flows

    def get_writer_prompt(
        self,
        key: str,
        coder_response: str,
        code_interpreter: BaseCodeInterpreter,
        config_template: Dict[str, str],
    ) -> str:
        """修正：处理代码输出为空的情况，优化参数传递逻辑"""
        # 获取代码执行结果，为空时用空字符串替代（避免None拼接）
        code_output = str(code_interpreter.get_code_output(key) or "")
        # 获取问题背景（确保存在该键，避免KeyError）
        bgc = str(self.questions.get("background", "未提供具体背景"))

        # 构建ques类写作提示（保持原始逻辑，修正类型问题）
        quesx_keys = self.get_questions_quesx_keys()
        quesx_writer_prompt = {
            ques_key: f"""
                问题背景：{bgc}
                不需要编写代码，代码手执行结果如下：
                1. 代码逻辑：{coder_response}
                2. 输出结果：{code_output}
                按照如下模板撰写：{config_template[ques_key]}
                要求：结果部分需量化，与代码输出一致，符合国赛规范
            """
            for ques_key in quesx_keys
        }

        # 通用写作提示（覆盖EDA、敏感性分析）
        writer_prompt = {
            "eda": f"""
                问题背景：{bgc}
                不需要编写代码，代码手执行结果如下：
                1. 数据处理逻辑：{coder_response}
                2. 统计与可视化结果：{code_output}
                按照如下模板撰写：{config_template["eda"]}
                要求：含统计指标、数据范围、结论及应用价值，无堆砌数据""",
            
            **quesx_writer_prompt,
            
            "sensitivity_analysis": f"""
                问题背景：{bgc}
                不需要编写代码，代码手执行结果如下：
                1. 敏感性分析逻辑：{coder_response}
                2. 参数变动与结果：{code_output}
                按照如下模板撰写：{config_template["sensitivity_analysis"]}
                要求：含参数类型、变动幅度、结果变化率，结论落地应用"""
        }

        if key in writer_prompt:
            return writer_prompt[key]
        raise ValueError(f"未知的任务类型: {key}，请检查流程配置")

    def get_questions_quesx_keys(self) -> List[str]:
        """修正：明确返回类型，保持筛选逻辑不变"""
        return list(self.get_questions_quesx().keys())

    def get_questions_quesx(self) -> Dict[str, Union[str, int]]:
        """修正：返回类型标注（匹配questions的value类型）"""
        return {
            key: value
            for key, value in self.questions.items()
            if key.startswith("ques") and key != "ques_count"
        }

    def get_seq(self, ques_count: int) -> Dict[str, str]:
        """修正：添加返回类型标注，保持原始逻辑"""
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
        ]
        return {key: "" for key in seq}