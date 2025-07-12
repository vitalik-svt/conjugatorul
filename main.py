from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types


class VerbConjugationForm(BaseModel):
    form: str
    pronoun: Optional[str] = None

class VerbConjugation(BaseModel):
    name: str
    types: List[VerbConjugationForm]

class Verb(BaseModel):
    name: str
    conjugations: List[VerbConjugation]

    @classmethod
    def from_verb(cls, verb_name: str) -> 'Verb':
        data = cls.get_conjugare_ro(verb_name)
        return cls.from_dict(data)

    def to_html(self) -> str:
        output = [f"<b>{self.name}</b>\n"]

        for conjugation in self.conjugations:
            output.append(f"\n<u>{conjugation.name}</u>")
            rows = []
            for form in conjugation.types:
                pronoun = form.pronoun or ""
                left = pronoun.ljust(20)
                right = form.form.rjust(20)
                rows.append(f"{left}{right}")
            if rows:
                output.append("<pre>" + "\n".join(rows) + "</pre>")

        return "\n".join(output)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Verb':
        conjugation_list = []

        for name, forms in data.get("conjugations", {}).items():
            types = [VerbConjugationForm(**form) for form in forms]
            conjugation = VerbConjugation(name=name, types=types)
            conjugation_list.append(conjugation)

        return cls(
            name=data.get("name"),
            conjugations=conjugation_list
        )

    @staticmethod
    def get_conjugare_ro(verb: str) -> dict:

        url = f"https://www.conjugare.ro/romana.php?conjugare={verb}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        conjugations = {}
        for box in soup.find_all("div", class_="box_conj"):
            tense_tag = box.find("b")
            if not tense_tag:
                continue
            tense_name = tense_tag.text.strip()
            forms = []
            for form_div in box.find_all("div", class_="cont_conj"):
                i_tag = form_div.find("i")
                if i_tag:
                    pronoun = i_tag.text.strip()
                    i_tag.extract()
                    form = form_div.text.strip()
                    forms.append({"pronoun": pronoun, "form": form})
                else:
                    forms.append({"form": form_div.text.strip()})
            conjugations[tense_name] = forms

        return {
            "name": verb,
            "conjugations": conjugations
        }


load_dotenv()

bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()

@dp.message()
async def conjugate(message: types.Message):
    await message.answer(Verb.from_verb(message.text).to_html(), parse_mode="HTML")


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
