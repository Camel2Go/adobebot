from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
import asyncio
from functools import partial
from io import BytesIO
from time import strftime
import discord
import totp

# drive the webdriver through the login pages
async def login(dirname, url, credentials, channel, log):

	log.info("logging in to creative cloud")
	await channel.send("[\U0001f468\u200d\U0001f4bb\ufe0f] opening new chrome session...")

	options = webdriver.ChromeOptions()
	options.add_argument("--headless=new")
	driver = webdriver.Chrome(options=options)

	try:
		await channel.send("[\U0001f4a4\ufe0f] fetching adobe's login page...")
		driver.get(url)

		WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, 'EmailForm')))
		assert driver.title == "Adobe ID", "title of adobe's login page is wrong!"

		await channel.send("[\U0001f47e\ufe0f] submitting email...")
		driver.find_element(by = By.ID, value = "EmailForm").find_element(by = By.ID, value = "EmailPage-EmailField").send_keys(credentials["email"])
		driver.find_element(by = By.ID, value = "EmailForm").find_element(by = By.CLASS_NAME, value = "spectrum-Button").click()

		await channel.send("[\U0001f4a4\ufe0f] waiting for shibboleth's login page...")
		WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, 'username')))
		assert driver.title == "Web login service for members of TUD Dresden University of Technology", "title of shibboleth's login page is wrong!"

		await channel.send("[\U0001f47e\ufe0f] filling in credentials...")
		driver.find_element(by = By.ID, value = "username").send_keys(credentials["user"])
		driver.find_element(by = By.ID, value = "password").send_keys(credentials["passwd"])
		#driver.find_element(by = By.ID, value = "donotcache").click()
		driver.find_element(by = By.XPATH, value = "//label[contains(@for,'donotcache')]").click()
		driver.find_element(by = By.NAME, value = "_eventId_proceed").click()

		await channel.send("[\U0001f4a4\ufe0f] waiting for shibboleth's TOTP page...")
		WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, 'fudis_otp_input')))
		assert driver.title == "Web login service for members of TUD Dresden University of Technology", "title of tu's shibboleth's TOTP page is wrong!"

		await channel.send("[\U0001f47e\ufe0f] filling in TOTP...")
		driver.find_element(by = By.ID, value = "fudis_otp_input").send_keys(totp.totp(credentials["totp"]))
		driver.find_element(by = By.NAME, value = "_eventId_proceed").click()

		await channel.send("[\U0001f4a4\ufe0f] waiting for adobe's confirmation page...")
		WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "description-big")))
		assert driver.title == "Adobe ID", "title of adobe's confirmation page is wrong!"

		if driver.find_element(By.CLASS_NAME, "spectrum-Heading1").text in ["Unbekannte Anmeldung", "Wait, there might be something suspicious"]:
			await channel.send("[\U0001f47e\ufe0f] permitting unknown login...")
			confirm = driver.find_element(By.CLASS_NAME, "spectrum-Button")
			assert confirm.text in ["Genehmigen Anmelden", "Approve login"], "button text of unknown-login page is wrong!"
			confirm.click()

			await channel.send("[\U0001f4a4\ufe0f] waiting again for adobe's confirmation page...")
			WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, "description-big")))
			assert driver.title == "Adobe ID", "title of adobe's confirmation page is wrong!"

		assert driver.find_element(By.CLASS_NAME, "spectrum-Heading1").text in ["Sie sind angemeldet", "You're signed in"], "text of adobe's confirmation is unexpected!"

		await channel.send("[\U0001f4af\ufe0f] successfully logged in :)")
		log.info("success")

	except Exception as e:
		log.exception(e)

		# save current page source for further examination
		with open(dirname + strftime("%Y-%m-%d_%H:%M:%S.html"), "w") as file:
			file.write(driver.page_source)

		# send message along with a screenshot of the current page
		await channel.send("[\u274c\ufe0f] an error occured!")
		await channel.send(file = discord.File(BytesIO(driver.get_screenshot_as_png()), "screenshot.png"))

	finally:
		# stop browser on success or error
		driver.quit()

