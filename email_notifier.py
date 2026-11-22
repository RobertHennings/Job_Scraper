import logging
import mimetypes
from pathlib import Path
import smtplib
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime, parseaddr

# Create logger
format_log = r"%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(
    format=format_log,
    force=True,
    filename=r"email_notifier.log",
    encoding="utf-8",
)
notifier_log = logging.getLogger("email_notifier")
notifier_log.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter(
    format_log,
)
# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
notifier_log.addHandler(ch)


class EmailNotifier:
    """A simple Email Service Notifier."""

    def __init__(
        self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str
    ) -> None:
        """Initial Parameters.

        Args:
            smtp_server (str): The SMTP server to use for sending emails.
            smtp_port (int): The port to use for the SMTP server.
            sender_email (str): The email address of the sender.
            sender_password (str): The password for the sender's email account.
        """
        self._validate_email_address(address=sender_email, field_name="sender_email")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def _validate_email_address(self, address: str, field_name: str) -> None:
        """Reject malformed or header-injection email addresses.

        Args:
            address (str): The email address to validate.
            field_name (str): The name of the field being validated (for error messages).

        Raises:
            ValueError: If the email address is malformed or contains line breaks.
            ValueError: If the email address is not valid.
        """
        if "\r" in address or "\n" in address:
            raise ValueError(f"{field_name} must not contain line breaks")

        _, parsed_address = parseaddr(address)
        if parsed_address != address or "@" not in parsed_address:
            raise ValueError(f"{field_name} is not a valid email address")
        else:
            notifier_log.info(f"Validated email address for {field_name}: {address}")

    def _encode_password(self, password: str) -> str:
        """Encode the password to URL readable format in case there are special
        characters. This is a simple encoding method for demonstration purposes.

        Args:
            password (str): The password to encode.
        """
        encoded_password = password.encode("utf-8")
        notifier_log.info("Encoded password for SMTP login.")
        return encoded_password

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Sequence[str | Path] | None = None,
        retry_count: int = 3,
        retry_delay: int = 5,
    ) -> None:
        """Send a plain-text email notification.

        Args:
            recipient_email (str): The email address of the recipient.
            subject (str): The subject of the email.
            body (str): The body of the email.
            attachments (Sequence[str | Path], optional): File paths to attach.
            retry_count (int, optional): The number of times to retry sending the email in case of failure. Defaults to 3.
            retry_delay (int, optional): The delay in seconds between retries. Defaults to 5
        """
        self._validate_email_address(
            address=recipient_email, field_name="recipient_email"
        )

        message = MIMEMultipart("mixed")
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message["Date"] = format_datetime(datetime.now(timezone.utc))
        message.attach(MIMEText(body, "html", "utf-8"))
        for attachment_path in attachments or ():
            try:
                notifier_log.info(f"Trying to attach file: {attachment_path}")
                path = Path(attachment_path)
                content_type, _ = mimetypes.guess_type(path.name)
                subtype = (
                    content_type.split("/", 1)[1]
                    if content_type and content_type.startswith("application/")
                    else "octet-stream"
                )
                with path.open("rb") as attachment_file:
                    attachment = MIMEApplication(
                        attachment_file.read(), _subtype=subtype
                    )
                attachment.add_header(
                    "Content-Disposition", "attachment", filename=path.name
                )
                message.attach(attachment)
            except Exception as e:
                notifier_log.error(
                    f"Failed to attach file {attachment_path}. Error: {str(e)}"
                )
                raise

        for attempt in range(retry_count):
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    notifier_log.info("Starting TLS connection to SMTP server.")
                    notifier_log.info("Logging in to SMTP server.")
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
                notifier_log.info(f"Email sent to {recipient_email}")
                return  # Exit the function if email is sent successfully
            except (OSError, smtplib.SMTPException) as e:
                notifier_log.warning(
                    f"Attempt {attempt + 1}: Failed to send email to {recipient_email}. Error: {str(e)}"
                )
                if attempt < retry_count - 1:
                    notifier_log.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    notifier_log.error(
                        f"Failed to send email to {recipient_email} after {retry_count} attempts"
                    )
                    self._validate_email_address(
                        address=recipient_email, field_name="recipient_email"
                    )
                    notifier_log.exception(
                        f"Failed to send email to {recipient_email} after {retry_count} attempts"
                    )
                    raise
