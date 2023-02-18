# import ai
from contextvars import ContextVar
from os import path
import adobe
import datetime
import discord
import json
import logging
import re

dirname = path.dirname(__file__) + "/"

# read credentials and authorization
credentials, authorized, to_track = json.loads(open(dirname + "data.json").read()).values()

# init openai
# ai.set_api_key(credentials["openai"])

# init discord client only subscribing to dms
intents = discord.Intents(dm_messages = True, members = True, presences = True, guilds = True)
client = discord.Client(intents=intents)


# init contextvar for author of message to be used inside other classes/functions
ctx_author = ContextVar("author", default = "unknown")

color_table = {
	discord.Status.online: discord.Color.green(),
	discord.Status.offline: discord.Color.dark_gray(),
	discord.Status.idle: discord.Color.gold(),
	discord.Status.dnd: discord.Color.red(),
}



# filter for using author of message in logging
class AuthorFilter(logging.Filter):
	def filter(self, record):
		record.author = str(ctx_author.get())
		return True

# init logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = logging.FileHandler(dirname + "bot.log")
fmt = logging.Formatter(fmt =  "[%(asctime)s] [%(levelname)-8s] %(author)-12s : %(message)s", datefmt = "%Y-%m-%d %H:%M:%S")
handler.setLevel(logging.INFO)
handler.setFormatter(fmt)
handler.addFilter(AuthorFilter())
log.addHandler(handler)


# event when bot is successfully logged in
@client.event
async def on_ready():
	ctx_author.set(client.user)
	log.info("successfully logged in")


# event when bot receives a message
@client.event
async def on_message(message):

	# we dont want to react to our own messages or group chats
	if message.author == client.user or not isinstance(message.channel, discord.channel.DMChannel):
		return

	# set the contextvar to the current author
	ctx_author.set(message.author)

	# handle requests for adobe
	if re.match("https:\/\/auth\.services\.adobe\.com\/[a-z]{2}_[A-Z]{2}\/deeplink\.html\?deeplink=ssofirst&callback", message.content) != None and str(message.author) in authorized["adobe"]:
		await adobe.login(dirname, message.content, credentials, message.channel, log)

	# handle requests for davinci-model
	# elif message.content in ["davinci", "prompt"] and str(message.author) in authorized["chatgpt"]:
	# 	await ai.prompt(message.content, message.channel, log)

	# handle requests for dalle-endpoint
	# elif message.content in ["dalle", "image"] and str(message.author) in authorized["chatgpt"]:
	# 	await ai.image(message.content, message.channel, log)

	else:
		log.info("\"" + message.content + "\"")
		await message.channel.send("\U0001f47a\ufe0f")
		
@client.event
async def on_presence_update(before, after):
	channel = client.get_channel(1076428584316583987)
	if str(after) in to_track:
		if before.mobile_status != after.mobile_status:
			await channel.send(embed = discord.Embed(title = after.name, description = "Handy ist jetzt " + str(after.mobile_status), color = color_table[after.mobile_status], timestamp = datetime.datetime.now()))
		if before.desktop_status != after.desktop_status:
			await channel.send(embed = discord.Embed(title = after.name, description = "Laptop ist jetzt " + str(after.desktop_status), color = color_table[after.desktop_status], timestamp = datetime.datetime.now()))
		if before.web_status != after.web_status:
			await channel.send(embed = discord.Embed(title = after.name, description = "Web-Session ist jetzt " + str(after.web_status), color = color_table[after.web_status], timestamp = datetime.datetime.now()))


if __name__ == "__main__":
	# run discord.py with bot-token and proper logging 
	client.run(credentials["discord"], log_handler = logging.FileHandler(dirname + "bot.log"))





