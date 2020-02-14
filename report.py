from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

from PIL import Image
import pandas as pd
import smtplib, ssl
import io

imgs = {}

def report_(df, DIR):

	sender_email = "zqretrace@gmail.com"
	receiver_email = "zqretrace@gmail.com, zach.barillaro@gmail.com, mp0941745@gmail.com, josephfalvo@outlook.com, lucasmduarte17@gmail.com, amandaxinvestment@gmail.com"
	receiver_email_list = ["zqretrace@gmail.com", "zach.barillaro@gmail.com", "mp0941745@gmail.com", "josephfalvo@outlook.com", "lucasmduarte17@gmail.com", "amandaxinvestment@gmail.com"]
	password = "Street1011"

	message = MIMEMultipart("alternative")
	message["Subject"] = "TWO CANDLE CLOSE SIGNALS"
	message["From"] = sender_email
	message["To"] = receiver_email

	html = f"""\
		<html>
			<body>
	"""

	for row in df.values:

		ticker, direction, avg = row

		img_ = None
		with io.BytesIO() as img_bytes:
			img_bytes = io.BytesIO()
			img = Image.open(f"{DIR}/plots/{ticker}.png", mode='r')
			img.save(img_bytes, format='PNG')
			img_ = img_bytes.getvalue()
		plot_ = img_

		html += f"""\
			<img src="cid:{ticker}">
			<br><br><br><br>
		"""

		imgs[ticker] = plot_

	html += f"""\
			</body>
		</html>
	"""

	message.attach(MIMEText(html, "html"))

	for ticker in imgs:
		
		msgImage = MIMEImage(imgs[ticker])
		msgImage.add_header('Content-ID', f'<{ticker}>')
		message.attach(msgImage)

		attachment = MIMEImage(imgs[ticker])
		attachment.add_header('Content-Disposition', 'attachment', filename=ticker)         
		message.attach(attachment)

	# Create secure connection with server and send email
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
		server.login(sender_email, password)
		server.sendmail(
			sender_email, receiver_email_list, message.as_string()
		)
