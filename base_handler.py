# handlers/base_handler.py

class BaseHandler:
    def __init__(self, bot, dp, sheets, gpt):
        self.bot = bot
        self.dp = dp
        self.sheets = sheets
        self.gpt = gpt
