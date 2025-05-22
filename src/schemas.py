from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    text: str

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    is_done: bool
    todolist_id: int

    class Config:
        orm_mode = True

class TodoListBase(BaseModel):
    name: str

class TodoListCreate(TodoListBase):
    pass

class TodoList(TodoListBase):
    id: int
    done_count: int
    total_count: int
    progress: float = 0.0
    items: List[Item] = []

    class Config:
        orm_mode = True
