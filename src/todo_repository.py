from sqlalchemy.orm import Session
from datetime import datetime

from .models import TodoList, Item
from .todo_aggregate import TodoListAggregate

class TodoListRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_aggregate(self, todolist_id: int) -> TodoListAggregate | None:
        todolist = self.db.query(TodoList).filter(
            TodoList.id == todolist_id,
            TodoList.deleted_at == None
        ).first()
        if not todolist:
            return None

        items = self.db.query(Item).filter(
            Item.todolist_id == todolist_id,
            Item.deleted_at == None
        ).all()

        return TodoListAggregate(
            id=todolist.id,
            name=todolist.name,
            done_count=todolist.done_count,
            total_count=todolist.total_count,
            items=items
        )

    def save(self, aggregate: TodoListAggregate):
        todolist = self.db.query(TodoList).filter(TodoList.id == aggregate.id).first()
        if not todolist:
            todolist = TodoList(
                id=aggregate.id,
                name=aggregate.name,
                done_count=aggregate.done_count,
                total_count=aggregate.total_count,
                deleted_at=None
            )
            self.db.add(todolist)
        else:
            todolist.name = aggregate.name
            todolist.done_count = aggregate.done_count
            todolist.total_count = aggregate.total_count
            todolist.deleted_at = None

        existing_items = {item.id: item for item in self.db.query(Item).filter(Item.todolist_id == aggregate.id).all()}

        for item in aggregate.items:
            if item.id in existing_items:
                exist = existing_items[item.id]
                exist.name = item.name
                exist.text = item.text
                exist.is_done = item.is_done
                exist.deleted_at = None
            else:
                self.db.add(item)

        self.db.commit()

    def soft_delete_todolist(self, todolist_id: int):
        todolist = self.db.query(TodoList).filter(
            TodoList.id == todolist_id,
            TodoList.deleted_at == None
        ).first()
        if todolist:
            todolist.deleted_at = datetime.utcnow()
            self.db.commit()

    def soft_delete_item(self, item_id: int):
        item = self.db.query(Item).filter(
            Item.id == item_id,
            Item.deleted_at == None
        ).first()
        if item:
            item.deleted_at = datetime.utcnow()
            self.db.commit()
