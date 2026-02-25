#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from visualdna_to_listing.crew import VisualdnaToListing

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information
def run_productresearchcrew():
    """
    Run the crew.
    """
    inputs = {
    }

    try:
        VisualdnaToListing().product_research_crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

def run_visualdnatolistingcrew():
    """
    Run the crew.
    """
    inputs = {
    }

    try:
        VisualdnaToListing().visualdna_to_listing_crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

def run_refindedresourcekittolistingcrew():
    """
    Run the crew.
    """
    inputs = {
    }

    try:
        VisualdnaToListing().refinded_resourcekit_to_listing_crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        VisualdnaToListing().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        VisualdnaToListing().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        VisualdnaToListing().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = VisualdnaToListing().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VisualDNA to Listing Crew")
    parser.add_argument("-r", action="store_true", help="Run product research crew")
    parser.add_argument("-g", action="store_true", help="Run visualdna to listing crew")
    parser.add_argument("-f", action="store_true", help="Run refined resourcekit to listing crew")
    args = parser.parse_args()
    
    if args.r:
        print("Running product research crew...")
        result = run_productresearchcrew()
    elif args.g:
        print("Running visualdna to listing crew...")
        result = run_visualdnatolistingcrew()
    elif args.f:
        print("Running refined resourcekit to listing crew...")
        result = run_refindedresourcekittolistingcrew()
    else:
        print("请选择要运行的 crew:")
        print("  1. Product Research Crew (输入 r)")
        print("  2. VisualDNA to Listing Crew (输入 g)")
        print("  3. Refined ResourceKit to Listing Crew (输入 f)")
        choice = input("请输入选择 (r/g/f): ").strip().lower()
        if choice == "r":
            print("Running product research crew...")
            result = run_productresearchcrew()
        elif choice == "g":
            print("Running visualdna to listing crew...")
            result = run_visualdnatolistingcrew()
        elif choice == "f":
            print("Running refined resourcekit to listing crew...")
            result = run_refindedresourcekittolistingcrew()
        else:
            print("无效选择，请输入 r、g 或 f")
            sys.exit(1)
    
    print("Result:", result)
