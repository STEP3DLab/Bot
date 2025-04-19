# models/order.py

class Order:
    def __init__(self, order_id, user_id, name, service, comment, status, date):
        self.order_id = order_id
        self.user_id = user_id
        self.name = name
        self.service = service
        self.comment = comment
        self.status = status
        self.date = date

    def to_list(self):
        return [self.order_id, self.user_id, self.name, self.service, self.comment, self.status, self.date]
