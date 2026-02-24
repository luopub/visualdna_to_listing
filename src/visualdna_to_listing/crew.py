from datetime import datetime
import json
import os
from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai.tools import tool
from .tools.custom_tool import HunyuanImageTool, UserInputTool, GetImageDescTool
import httpx
from crewai.llms.hooks import BaseInterceptor
from .tools.my_file_read_tool import MyFileReadTool as FileReadTool
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
file_read_tool = FileReadTool(encoding="utf-8")  # Example of initializing the file read tool with UTF-8 encoding
image_generator_tool = HunyuanImageTool()
user_input_tool = UserInputTool()
get_image_desc_tool = GetImageDescTool()

@tool
def image_generator_tool2(prompts: str, reference_images: list[str] | None=None, saved_images: list[str] | None=None) -> None:
    """Useful for when you need to generate images based on prompts and reference images."""
    # In a real application, this would call an image generation API
    print(f"Generating images for prompts: {prompts}")
    print(f"Using reference images: {reference_images}")
    print(f"Saving images to: {saved_images}")

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

# Create QWEN LLM using native OpenAI provider with custom base_url
llm = LLM(model="qwen3.5-plus",
        api_key=os.environ.get("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        interceptor=CustomInterceptor()
        )

@CrewBase
class VisualdnaToListing():
    """VisualdnaToListing crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def product_research_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['product_research_specialist'], # type: ignore[index]
            verbose=True,
            llm=llm,
            tools=[search_tool, scrape_tool,user_input_tool],
            allow_delegation=False
        )
    
    @agent
    def strategic_visual_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['strategic_visual_planner'], # type: ignore[index]
            verbose=True,
            llm=llm,
            tools=[file_read_tool],
            allow_delegation=False
        )

    @task
    def market_intelligence_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_intelligence_task'], # type: ignore[index]
        )
    @task
    def resource_kit_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config['resource_kit_generation_task'], # type: ignore[index]
            output_file='resource_kit_researched.md',
        )
    @crew
    def product_research_crew(self) -> Crew:
        """Creates the VisualdnaToListing crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            # agents=self.agents, # Automatically created by the @agent decorator
            agents=[self.product_research_specialist(), self.strategic_visual_planner()],
            # tasks=self.tasks, # Automatically created by the @task decorator
            tasks=[self.market_intelligence_task(), self.resource_kit_generation_task()],
            # tasks=[*self.tasks[2:]],  #, self.define_visual_dna_task, self.plan_and_write_prompts_task, self.generate_listing_images_task],
            process=Process.sequential,
            verbose=True,
        )

    @agent
    def product_info_collector(self) -> Agent:
        print("Creating product_info_collector agent with access to file_read_tool and user_input_tool...", self.agents_config)
        return Agent(
            config=self.agents_config['product_info_collector'],
            verbose=True,
            tools=[get_image_desc_tool],
            llm=llm
        )

    # If you would like to add tools to your agents, you can learn more about it here:
    @agent
    def visual_dna_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['visual_dna_architect'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    @agent
    def creative_prompt_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['creative_prompt_engineer'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    @agent
    def image_production_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['image_production_specialist'], # type: ignore[index]
            verbose=True,
            llm=llm
        )

    @task
    def collect_product_info_task(self) -> Task:
        return Task(
            config=self.tasks_config['collect_product_info_task'],
            tools=[file_read_tool, user_input_tool],
            # output_file="resource_kit_refined.md",
        )
    
    @task
    def reference_photo_description_task(self) -> Task:
        return Task(
            config=self.tasks_config['reference_photo_description_task'], # type: ignore[index]
        )

    @task
    def confirm_and_save_facts_task(self) -> Task:
        return Task(
            config=self.tasks_config['confirm_and_save_facts_task'], # type: ignore[index]
            tools=[user_input_tool],
            output_file="resource_kit_refined.md",
        )

    @task
    def define_visual_dna_task(self) -> Task:
        return Task(
            config=self.tasks_config['define_visual_dna_task'], # type: ignore[index]
            tools=[file_read_tool] # Example of how to add tools to a task, which will be passed to the assigned agent(s
        )

    @task
    def plan_and_write_prompts_task(self) -> Task:
        return Task(
            config=self.tasks_config['plan_and_write_prompts_task'], # type: ignore[index]
            tools=[file_read_tool]
        )

    @task
    def image_prompts_review_task(self) -> Task:
        return Task(
            config=self.tasks_config['image_prompts_review_task'], # type: ignore[index]
            tools=[file_read_tool]
        )

    @task
    def generate_listing_images_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_listing_images_task'], # type: ignore[index]
            tools=[image_generator_tool] # Example of how to add tools to a task, which will be passed to the assigned agent(s)
        )

    @crew
    def visualdna_to_listing_crew(self) -> Crew:
        """Creates the VisualdnaToListing crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            # agents=self.agents, # Automatically created by the @agent decorator
            agents=[self.product_info_collector(), self.visual_dna_architect(), self.creative_prompt_engineer(), self.image_production_specialist()],
            # tasks=self.tasks, # Automatically created by the @task decorator
            tasks=[self.collect_product_info_task(), self.reference_photo_description_task(), self.confirm_and_save_facts_task(), self.define_visual_dna_task(), self.plan_and_write_prompts_task(), self.image_prompts_review_task(), self.generate_listing_images_task()],
            # tasks=[*self.tasks[2:]],  #, self.define_visual_dna_task, self.plan_and_write_prompts_task, self.generate_listing_images_task],
            process=Process.sequential,
            verbose=True,
        )
