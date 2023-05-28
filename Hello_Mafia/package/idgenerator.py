import threading

EXTEND_COEF = 1.5


class IdGenerator:
    def __init__(self):
        self.id_set = set([i for i in range(1, 5, 1)])
        self.max_value = 4
        self.lock = threading.Lock()

    def add_new_values(self) -> None:
        new_max_value = int(self.max_value * EXTEND_COEF)
        for i in range(self.max_value, new_max_value):
            self.id_set.add(i)
        self.max_value = new_max_value

    def get_id(self) -> int:
        with self.lock:
            if len(self.id_set) == 0:
                self.add_new_values()
            return self.id_set.pop()

    def add_id(self, _id: int) -> None:
        with self.lock:
            self.id_set.add(_id)

    def count_active_players(self):
        with self.lock:
            return self.max_value - len(self.id_set)
