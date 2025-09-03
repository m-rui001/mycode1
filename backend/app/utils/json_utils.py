import json
from json import JSONDecodeError
from typing import Any, Dict, List

class SafeJSON:
    @staticmethod
    def loads(s: str, strict: bool = True) -> Dict[str, Any]:
        """安全解析JSON字符串，自动修复常见错误"""
        try:
            return json.loads(s, strict=strict)
        except JSONDecodeError as e:
            # 尝试修复单引号问题
            if "'" in s:
                fixed = s.replace("'", '"')
                try:
                    return json.loads(fixed, strict=strict)
                except JSONDecodeError:
                    pass
            # 尝试修复尾部逗号问题
            if e.msg == "Trailing comma" and strict:
                fixed = s[:e.pos-1] + s[e.pos:]
                try:
                    return json.loads(fixed, strict=False)
                except JSONDecodeError:
                    pass
            raise RuntimeError(f"JSON解析失败：{str(e)}") from e

    @staticmethod
    def dumps(obj: Any, ensure_ascii: bool = False, **kwargs) -> str:
        """安全序列化JSON，确保中文正常显示"""
        return json.dumps(obj, ensure_ascii=ensure_ascii,** kwargs)

# 全局实例
safe_json = SafeJSON()