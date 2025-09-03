import request from "@/utils/request";

export function submitModelingTask(
	problem: {
		ques_all: string;
		comp_template?: string;
		format_output?: string;
	},
	files?: File[],
) {
	const formData = new FormData();
	// 添加问题数据
	formData.append("ques_all", problem.ques_all);
	formData.append("comp_template", problem.comp_template || 'CHINA');
	formData.append("format_output", problem.format_output || "Markdown");

	// 添加文件（如有）
	if (files && files.length > 0) {
		for (const file of files) {
			formData.append("files", file);
		}
	}

	// 始终返回请求，修复无文件时无返回值的问题
	return request.post<{
		task_id: string;
		status: string;
	}>("/modeling", formData, {
		headers: {
			"Content-Type": "multipart/form-data",
		},
		timeout: 30000,
	});
}
