# services/sheets_service.py

from models.order import Order

class SheetsService:
    def __init__(self, key, creds_file):
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)

        self.order_sheet = client.open_by_key(key).worksheet("Заказы_бота")
        self.log_sheet = client.open_by_key(key).worksheet("GPT_лог")

    def save_order(self, order: Order):
        self.order_sheet.append_row(order.to_list())

    def list_orders(self, user_id=None):
        rows = self.order_sheet.get_all_records()
        return [
            Order(r['№'], r['user_id'], r['name'], r['service'], r['comment'], r['статус'], r['дата'])
            for r in rows if not user_id or str(r['user_id']) == str(user_id)
        ]

    def update_order_status(self, order_id, status):
        rows = self.order_sheet.get_all_records()
        idx = next((i+2 for i, r in enumerate(rows) if str(r['№']) == str(order_id)), None)
        if idx:
            self.order_sheet.update_cell(idx, 6, status)
            return True
        return False

    def delete_order(self, order_id):
        rows = self.order_sheet.get_all_records()
        idx = next((i+2 for i, r in enumerate(rows) if str(r['№']) == str(order_id)), None)
        if idx:
            self.order_sheet.delete_row(idx)
            return True
        return False

    def log_gpt(self, user_id, question, answer):
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        next_id = len(self.log_sheet.get_all_values())
        self.log_sheet.append_row([next_id, user_id, question, answer, now])
