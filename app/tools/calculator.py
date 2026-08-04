from langchain_core.tools import tool
from app.tools.schemas import caculate_data


@tool(args_schema=caculate_data)
def caculate_number(a: int, b: int, c: str):
    """计算两个数的数学运算"""
    if c == "+":
        return str(a + b)
    elif c == "-":
        return str(a - b)
    elif c == "*":
        return str(a * b)
    elif c == "/":
        if b == 0:
            return "错误：除数不能为零"
        return str(a / b)
    else:
        return f"不支持的运算: {c}"
