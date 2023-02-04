from contextvars import ContextVar
from functools import partial
from io import BytesIO
from os import path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
import asyncio
import discord
import json
import logging
import time

class AuthorFilter(logging.Filter):
	def filter(self, record):
		record.author = str(ctx_author.get())
		return True

dirname = path.dirname(__file__) + "/"

authorized = json.loads(open(dirname + "authorized.json").read())
credentials = json.loads(open(dirname + "credentials.json").read())

intents = discord.Intents.default()
client = discord.Client(intents=intents)

options = FirefoxOptions()
options.add_argument('--headless')

ctx_author = ContextVar("author", default = "unknown")

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = logging.FileHandler(dirname + "bot.log")
fmt = logging.Formatter(fmt =  "[%(asctime)s] [%(levelname)-8s] %(author)-12s : %(message)s", datefmt = "%Y-%m-%d %H:%M:%S")
handler.setLevel(logging.INFO)
handler.setFormatter(fmt)
handler.addFilter(AuthorFilter())
log.addHandler(handler)


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


@client.event
async def on_ready():
	ctx_author.set(client.user)
	log.info("successfully logged in")


@client.event
async def on_message(message):

	if message.author == client.user or not isinstance(message.channel, discord.channel.DMChannel):
		return

	ctx_author.set(message.author)

	if str(message.author) not in authorized:
		log.info("unauthorized, content: \"" + message.content + "\"")
		await message.channel.send("[\U0001f47a\ufe0f] unauthorized!")
	
	elif "https://auth.services.adobe.com/de_DE/deeplink.html?deeplink=ssofirst&callback" not in message.content:
		log.info("not a valid url, content: \"" + message.content + "\"")
		await message.channel.send("[\U0001f47a\ufe0f] not a valid url!")

	else:

		log.info("logging in to creative cloud")
		await message.channel.send("[\U0001f468\u200d\U0001f4bb\ufe0f] opening new firefox session...")
		
		driver = await asyncio.get_running_loop().run_in_executor(None, partial(webdriver.Firefox, options = options))

		try:
			await login(driver, message.content, message.channel)
			log.info("success")

		except (TimeoutException, AssertionError) as e:
			log.exception(e)
			with open(dirname + time.strftime("%Y-%m-%d_%H:%M:%S.html"), "w") as file:
				file.write(driver.page_source)
			await message.channel.send("[\u274c\ufe0f] an error occured!")
			await message.channel.send(file = discord.File(BytesIO(driver.get_screenshot_as_png()), "screenshot.png"))

		finally:
			driver.quit()


if __name__ == "__main__":

	client.run(credentials["token"], log_handler = logging.FileHandler(dirname + "bot.log"))





