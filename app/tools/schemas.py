from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    query: str = Field(description="要在知识库中检索的问题，例如：'agent是什么'")


class SearchWebInput(BaseModel):
    query: str = Field(description="要搜索的关键词")


class WeatherInput(BaseModel):
    city: str = Field(description="城市名称，例如：北京、上海、东京")


class caculate_data(BaseModel):
    a: int = Field(description="第一个数字")
    b: int = Field(description="第二个数字")
    c: str = Field(description="+就是相加,-就是相减,*就是相乘,/就是相除")
