import os
import google.generativeai as genai
import hashlib
import json
import logging
from typing import Dict, List, Optional
from functools import lru_cache

class AIResponseManager:
    def __init__(self, config: Dict):
        self.api_key = config["gemini_api_key"]
        if not self.api_key:
            raise ValueError("Gemini API key not found. Please set it in config.json.")
        genai.configure(api_key=self.api_key)
        self.max_tokens = config.get("max_tokens", 8192)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        self.generation_config = genai.GenerationConfig(
            max_output_tokens=self.max_tokens,
            temperature=0.7,
        )
        self.cache = AIResponseCache()

    async def generate_response(self, messages: List[Dict]) -> str:
        try:
            cache_key = self.cache._get_cache_key(json.dumps(messages))
            if cache_key in self.cache.cache:
                return self.cache.cache[cache_key]

            response = self.model.generate_content(
                contents=messages,
                generation_config=self.generation_config,
            )
            response_content = response.text.strip()
            self.cache.cache[cache_key] = response_content
            return response_content

        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return f"[Error generating response: {str(e)}]"

class ChatGPT:
    def __init__(self, config: Dict):
        self.ai_manager = AIResponseManager(config)

    async def get_response(self, messages: List[Dict]) -> str:
        return await self.ai_manager.generate_response(messages)

class PromptManager:
    def __init__(self):
        self.base_prompts = {
            "witness_testimony": """
You are {witness_name}, a witness with {personality_traits} traits.
Your stress level is {stress}/10.
Backstory: {backstory}
Relationship with defendant: {relationship}.

{personality_instructions}

Relevant Case Context: {case_context}

Previous testimony context:
{previous_testimony}

Current question: {question}

Respond in character, maintaining all aspects above.
{reveal_motive_hint}
""",
            "judge_ruling": """
You are presiding over a case involving {case_type}.
Consider:
1. The objection type: {objection_type}
2. The specific question: {question}
3. Legal precedent and rules of evidence

Provide a ruling (Sustained/Overruled) with a brief explanation.
"""
        }

    def generate_prompt(self, prompt_type: str, context: Dict) -> List[Dict]:
        if prompt_type not in self.base_prompts:
            logging.error(f"Prompt type '{prompt_type}' not defined.")
            raise ValueError(f"Prompt type '{prompt_type}' not defined.")

        if prompt_type == "witness_testimony":
            context["personality_instructions"] = self.get_personality_instructions(context["personality_traits"])
            context["reveal_motive_hint"] = "You are thinking about your hidden motive: " + context["hidden_motive"] + "." if context["stress"] > 7 and context.get("hidden_motive") else ""

        formatted_prompt = self.base_prompts[prompt_type].format(**context)
        return [{"role": "user", "parts": [formatted_prompt]}]

    def get_personality_instructions(self, personalities: List[str]) -> str:
        instructions = []
        for p in personalities:
            if p == "Nervous":
                instructions.append("Stammer or hesitate occasionally.")
            elif p == "Defensive":
                instructions.append("Be resistant to aggressive questioning, and try to deflect the question or minimize your involvement.")
            elif p == "Calm":
                instructions.append("Maintain a composed demeanor, answering clearly and directly.")
            elif p == "Cooperative":
                instructions.append("Answer questions willingly and provide as much detail as possible.")
            elif p == "Aggressive":
                instructions.append("Be confrontational and challenge the questions when possible.")
            elif p == "Evasive":
                instructions.append("Try to avoid giving direct answers, and change the subject if possible.")
            elif p == "Honest":
                instructions.append("Answer truthfully, even if it reveals damaging information.")
            elif p == "Deceitful":
                instructions.append("Provide misleading or false information when you think it benefits you or the person you are protecting. Do not contradict previous statements if possible.")

        return " ".join(instructions)

class AIResponseCache:
    def __init__(self):
        self.cache = {}

    def _get_cache_key(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()