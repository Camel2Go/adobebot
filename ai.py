import openai

model = "text-davinci-003"
tokens = 1000
size = "1024x1024"

def set_api_key(api_key):
    openai.api_key = api_key



# talk to chatgpt
async def prompt(prompt, channel, log):

    try:
        completion_resp = await openai.Completion.acreate(prompt = prompt, max_tokens = tokens, engine = model)
        return completion_resp.choices[0].text

    except (openai.error.RateLimitError):
        pass

async def image(prompt, channel, log):
    
    try:
        image_resp = await openai.Image.acreate(prompt = prompt, n = 4, size = size, response_format = "b64_json")
        return response['data']
    except (openai.error.InvalidRequestError):
        pass