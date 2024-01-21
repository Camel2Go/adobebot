import time
import hmac
import base64

def totp(secret, digits = 6, digest = 'sha1'):
	key = base64.b32decode(secret)
	message = int(time.time() / 30).to_bytes(8, 'big')
	mac = hmac.digest(key, message, digest)
	index = mac[-1] & 0b1111
	value = int.from_bytes(mac[index:index + 4]) & 0x7fffffff
	return value % (10 ** digits)