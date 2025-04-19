# services/gpt_service.py

from openai import OpenAI

class GPTService:
    def __init__(self, api_key, model='gpt-4.1-nano-2025-04-14'):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def ask(self, prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты — эксперт по 3D-печати."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
