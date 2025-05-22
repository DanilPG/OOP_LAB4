from typing import List
from .models import Item
from datetime import datetime

class TodoListAggregate:
    def __init__(self, id: int, name: str, done_count: int, total_count: int, items: List[Item]):
        self.id = id
        self.name = name
        self.done_count = done_count
        self.total_count = total_count
        self.items = items

    @property
    def progress(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.done_count / self.total_count) * 100

    def add_item(self, item: Item):
        self.items.append(item)
        self.total_count += 1
        if item.is_done:
            self.done_count += 1

    def update_item(self, item_id: int, name: str, text: str, is_done: bool):
        for item in self.items:
            if item.id == item_id:
                # пересчитываем done_count, если меняется статус
                if item.is_done != is_done:
                    if is_done:
                        self.done_count += 1
                    else:
                        self.done_count -= 1
                item.name = name
                item.text = text
                item.is_done = is_done
                break

    def soft_delete_item(self, item_id: int):
        for i, item in enumerate(self.items):
            if item.id == item_id:
                if item.is_done:
                    self.done_count -= 1
                self.total_count -= 1
                self.items.pop(i)
                break
