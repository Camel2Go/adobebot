from contextvars import ContextVar
from functools import partial
from io import BytesIO
from os import path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from time import strftime
import asyncio
import discord
import json
import logging

# filter for using author of message in logging
class AuthorFilter(logging.Filter):
	def filter(self, record):
		record.author = str(ctx_author.get())
		return True

dirname = path.dirname(__file__) + "/"

# read credentials and authorization
authorized = json.loads(open(dirname + "authorized.json").read())
credentials = json.loads(open(dirname + "credentials.json").read())

# init discord client only subscribing to dms
intents = discord.Intents(dm_messages = True)
client = discord.Client(intents=intents)

# headless firefox is fine
options = webdriver.FirefoxOptions()
options.add_argument('--headless')

# init contextvar for author of message to be used inside other classes/functions
ctx_author = ContextVar("author", default = "unknown")

# init logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = logging.FileHandler(dirname + "bot.log")
fmt = logging.Formatter(fmt =  "[%(asctime)s] [%(levelname)-8s] %(author)-12s : %(message)s", datefmt = "%Y-%m-%d %H:%M:%S")
handler.setLevel(logging.INFO)
handler.setFormatter(fmt)
handler.addFilter(AuthorFilter())
log.addHandler(handler)


# drive the webdriver through adobes login crap
async def login(driver, url, channel):
	
	await channel.send("[\U0001f4a4\ufe0f] fetching adobe's login page...")
	driver.get(url)

	WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.ID, 'EmailForm')))
	assert driver.title == "Adobe ID", "title of login page was wrong!"
	
	await channel.send("[\U0001f47e\ufe0f] submitting email...")
	driver.find_element(by = By.ID, value = "EmailForm").find_element(by = By.ID, value = "EmailPage-EmailField").send_keys(credentials["email"])
	driver.find_element(by = By.ID, value = "EmailForm").find_element(by = By.CLASS_NAME, value = "spectrum-Button").click()

	await channel.send("[\U0001f4a4\ufe0f] waiting for shibboleth's login page...")
	WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, 'username')))
	assert driver.title == "Web login service for members of Technische Universität Dresden", "title of shibboleth was wrong!"

	await channel.send("[\U0001f47e\ufe0f] filling in credentials...")
	driver.find_element(by = By.ID, value = "username").send_keys(credentials["user"])
	driver.find_element(by = By.ID, value = "password").send_keys(credentials["passwd"])
	driver.find_element(by = By.NAME, value = "donotcache").click()
	driver.find_element(by = By.NAME, value = "_eventId_proceed").click()

	await channel.send("[\U0001f4a4\ufe0f] waiting for adobe's confirmation page...")
	WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "description-big")))
	assert driver.title == "Adobe ID", "title of confirmation page was wrong!"
	
	if driver.find_element(By.CLASS_NAME, "spectrum-Heading1").text == "Unbekannte Anmeldung":
		await channel.send("[\U0001f47e\ufe0f] permitting unknown login...")
		confirm = driver.find_element(By.CLASS_NAME, "spectrum-Button")
		assert confirm.text == "Genehmigen Anmelden", "button text of unknown-login page was wrong!"
		confirm.click()

	await channel.send("[\U0001f4a4\ufe0f] waiting again for adobe's confirmation page...")
	WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "description-big")))
	assert driver.find_element(By.CLASS_NAME, "spectrum-Heading1").text == "Sie sind angemeldet", "text of confirmation page was unexpected!"
	
	await channel.send("[\U0001f4af\ufe0f] all done :)")


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

	# we dont answer anyone, sorry
	if str(message.author) not in authorized:
		log.info("unauthorized, content: \"" + message.content + "\"")
		await message.channel.send("[\U0001f47a\ufe0f] unauthorized!")
	
	# we dont need to call every bullshit website that is given to us
	elif "https://auth.services.adobe.com/de_DE/deeplink.html?deeplink=ssofirst&callback" not in message.content:
		log.info("not a valid url, content: \"" + message.content + "\"")
		await message.channel.send("[\U0001f47a\ufe0f] not a valid url!")

	# all fine, lets go!
	else:
		log.info("logging in to creative cloud")
		await message.channel.send("[\U0001f468\u200d\U0001f4bb\ufe0f] opening new firefox session...")
		
		# init firefox, to it async to avoid "Shard ID None heartbeat blocked for more than 10 seconds."
		driver = await asyncio.get_running_loop().run_in_executor(None, partial(webdriver.Firefox, options = options, service_log_path = dirname + "geckodriver.log"))

		try:
			await login(driver, message.content, message.channel)
			log.info("success")

		except (TimeoutException, AssertionError) as e:
			log.exception(e)

			# save current page source for further examination
			with open(dirname + time.strftime("%Y-%m-%d_%H:%M:%S.html"), "w") as file:
				file.write(driver.page_source)
			
			# send message along with a screenshot of the current page
			await message.channel.send("[\u274c\ufe0f] an error occured!")
			await message.channel.send(file = discord.File(BytesIO(driver.get_screenshot_as_png()), "screenshot.png"))

		finally:
			# stop firefox on success, as well as on error
			driver.quit()


if __name__ == "__main__":
	# run discord.py with bot-token and proper logging 
	client.run(credentials["token"], log_handler = logging.FileHandler(dirname + "bot.log"))





