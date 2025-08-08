import openai

def get_openai_client(api_key: str):
    return openai.OpenAI(api_key=api_key)

def generate_response(client, prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты весёлый, находчивый скандинавский историк, который обожает доказывать, "
                    "что абсолютно любое имя — на самом деле скандинавское. "
                    "Отвечай с юмором, пафосом, упоминай мифологию, викингов, богов и обязательно "
                    "придумывай древние (вымышленные) истории. Можешь использовать эмодзи и старинный стиль речи. "
                    "Будь харизматичен и убедителен, но не злой."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=1.1,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


# def generate_response(client, prompt: str) -> str:
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.9,
#         max_tokens=500,
#     )
#     return response.choices[0].message.content.strip()
