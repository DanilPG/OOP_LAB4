from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import database, schemas, models
from .todo_repository import TodoListRepository
from .todo_aggregate import TodoListAggregate

router = APIRouter()

@router.post("/todolists/", response_model=schemas.TodoList)
def create_todolist(todolist: schemas.TodoListCreate, db: Session = Depends(database.get_db)):
    repo = TodoListRepository(db)
    new_todolist = models.TodoList(
        name=todolist.name,
        done_count=0,
        total_count=0,
        deleted_at=None
    )
    db.add(new_todolist)
    db.commit()
    db.refresh(new_todolist)

    aggregate = TodoListAggregate(
        id=new_todolist.id,
        name=new_todolist.name,
        done_count=0,
        total_count=0,
        items=[]
    )

    return schemas.TodoList(
        id=aggregate.id,
        name=aggregate.name,
        done_count=aggregate.done_count,
        total_count=aggregate.total_count,
        progress=aggregate.progress,
        items=[]
    )

@router.get("/todolists/", response_model=List[schemas.TodoList])
def get_todolists(db: Session = Depends(database.get_db)):
    todolists = db.query(models.TodoList).filter(models.TodoList.deleted_at == None).all()
    results = []
    for todolist in todolists:
        progress = (todolist.done_count / todolist.total_count * 100) if todolist.total_count > 0 else 0
        todo_schema = schemas.TodoList.from_orm(todolist).copy(update={"progress": progress, "items": []})
        results.append(todo_schema)
    return results

@router.get("/todolists/{todolist_id}", response_model=schemas.TodoList)
def get_todolist(todolist_id: int, db: Session = Depends(database.get_db)):
    todolist = db.query(models.TodoList).filter(
        models.TodoList.id == todolist_id,
        models.TodoList.deleted_at == None
    ).first()
    if not todolist:
        raise HTTPException(status_code=404, detail="TodoList not found")
    items = db.query(models.Item).filter(
        models.Item.todolist_id == todolist_id,
        models.Item.deleted_at == None
    ).all()

    progress = (todolist.done_count / todolist.total_count * 100) if todolist.total_count > 0 else 0

    return schemas.TodoList(
        id=todolist.id,
        name=todolist.name,
        done_count=todolist.done_count,
        total_count=todolist.total_count,
        progress=progress,
        items=items
    )

@router.post("/todolists/{todolist_id}/items/", response_model=schemas.Item)
def create_item(todolist_id: int, item: schemas.ItemCreate, db: Session = Depends(database.get_db)):
    repo = TodoListRepository(db)
    aggregate = repo.get_aggregate(todolist_id)
    if not aggregate:
        raise HTTPException(status_code=404, detail="TodoList not found")

    new_item = models.Item(
        name=item.name,
        text=item.text,
        is_done=False,
        todolist_id=todolist_id,
        deleted_at=None
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # обновляем агрегат
    aggregate.add_item(new_item)
    repo.save(aggregate)

    return schemas.Item.from_orm(new_item)

@router.patch("/todolists/{todolist_id}/items/{item_id}", response_model=schemas.Item)
def update_item(todolist_id: int, item_id: int, item: schemas.ItemCreate, db: Session = Depends(database.get_db)):
    repo = TodoListRepository(db)
    aggregate = repo.get_aggregate(todolist_id)
    if not aggregate:
        raise HTTPException(status_code=404, detail="TodoList not found")

    db_item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.todolist_id == todolist_id,
        models.Item.deleted_at == None
    ).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Проверим изменился ли is_done
    is_done = getattr(item, 'is_done', db_item.is_done)  # если is_done есть, иначе оставим старое (у нас в ItemCreate нет is_done, так можно добавить в схему)

    # Для упрощения добавим is_done в схему ItemCreate:
    # class ItemCreate(ItemBase):
    #     is_done: Optional[bool] = False

    # Обновляем поля
    db_item.name = item.name
    db_item.text = item.text
    if hasattr(item, "is_done"):
        db_item.is_done = item.is_done

    db.commit()
    db.refresh(db_item)

    # обновляем агрегат и счетчики
    aggregate.update_item(item_id, db_item.name, db_item.text, db_item.is_done)
    repo.save(aggregate)

    return schemas.Item.from_orm(db_item)

@router.delete("/todolists/{todolist_id}/items/{item_id}")
def delete_item(todolist_id: int, item_id: int, db: Session = Depends(database.get_db)):
    repo = TodoListRepository(db)
    aggregate = repo.get_aggregate(todolist_id)
    if not aggregate:
        raise HTTPException(status_code=404, detail="TodoList not found")

    db_item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.todolist_id == todolist_id,
        models.Item.deleted_at == None
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Мягкое удаление
    repo.soft_delete_item(item_id)
    aggregate.soft_delete_item(item_id)
    repo.save(aggregate)

    return {"detail": "Item soft deleted"}

@router.delete("/todolists/{todolist_id}")
def delete_todolist(todolist_id: int, db: Session = Depends(database.get_db)):
    repo = TodoListRepository(db)
    repo.soft_delete_todolist(todolist_id)
    return {"detail": "TodoList soft deleted"}
