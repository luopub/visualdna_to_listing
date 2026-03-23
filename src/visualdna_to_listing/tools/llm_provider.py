import os
from crewai import LLM
import httpx
from crewai.llms.hooks import BaseInterceptor
from datetime import datetime
import json

class CustomInterceptor(BaseInterceptor[httpx.Request, httpx.Response]):
    def __init__(self, *args, **kwargs):
        # The log file name ends with date time
        self.llm_log_path = "llm_log_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        self.llm_log = []
        super().__init__(*args, **kwargs)

    def on_outbound(self, request: httpx.Request) -> httpx.Request:
        """Print request before sending to the LLM provider."""
        # print(request)
        log_idx = len(self.llm_log) // 2
        self.llm_log.append({f"request_{log_idx}": json.loads(request.content)})
        with open(self.llm_log_path, "w", encoding="utf-8") as f:
            json.dump(self.llm_log, f, indent=4)
        return request

    def on_inbound(self, response: httpx.Response) -> httpx.Response:
        """Process response after receiving from the LLM provider."""
        # print(f"Status: {response.status_code}")
        # print(f"Response time: {response.elapsed}")
        return response


# Create Kimi LLM using native OpenAI provider with custom base_url
# llm = LLM(model="kimi-k2.5",
#         api_key=os.environ.get("MOONSHOT_API_KEY"),
#         base_url="https://api.moonshot.cn/v1",
#         interceptor=CustomInterceptor()
#         )

# Create GLM LLM using native OpenAI provider with custom base_url
# llm = LLM(model="GLM-4.6V",
#         api_key=os.environ.get("ZAI_API_KEY"),
#         base_url="https://open.bigmodel.cn/api/paas/v4/",
#         interceptor=CustomInterceptor()
#         )

class LLMProvider:
    llm_main: LLM | None = None
    llm_vision: LLM | None = None

    @classmethod
    def get_llm_main(cls) -> LLM:
        if cls.llm_main is None:
            # 检查API密钥
            if not os.environ.get("DASHSCOPE_API_KEY"):
                print("错误: 未设置 DASHSCOPE_API_KEY 环境变量")
                print("请先设置环境变量:")
                print("  Windows: set DASHSCOPE_API_KEY=your-api-key")
                print("  Linux/Mac: export DASHSCOPE_API_KEY=your-api-key")
                raise Exception("DASHSCOPE_API_KEY environment variable not set")
            cls.llm_main = LLM(
                model="qwen3.5-plus",
                api_key=os.environ.get("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                interceptor=CustomInterceptor()
            )
        return cls.llm_main


    @classmethod
    def get_llm_vision(cls) -> LLM:
        if cls.llm_vision is None:
            # 检查API密钥
            if not os.environ.get("DASHSCOPE_API_KEY"):
                print("错误: 未设置 DASHSCOPE_API_KEY 环境变量")
                print("请先设置环境变量:")
                print("  Windows: set DASHSCOPE_API_KEY=your-api-key")
                print("  Linux/Mac: export DASHSCOPE_API_KEY=your-api-key")
                raise Exception("DASHSCOPE_API_KEY environment variable not set")
            # Create QWEN LLM using native OpenAI provider with custom base_url
            cls.llm_vision = LLM(model="qwen3.5-plus",
                    api_key=os.environ.get("DASHSCOPE_API_KEY"),
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    )
        return cls.llm_vision