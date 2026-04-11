import time
from fastapi import APIRouter, Depends, HTTPException
from bitnote.core.database import get_db
from fastapi import Body
from pydantic import BaseModel
import json
import uuid
import threading

import os
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path

from bitnote.core.security import get_current_user
from bitnote.schemas.learning_plan import LearningPlanRequest
from bitnote.services.educational_ai.learning_plan_service import generate_learning_plan
from bitnote.services.educational_ai.description_service import (
    generate_notebook_description,
)
from bitnote.services.educational_ai.summarize_service import (
    generate_summary_with_ollama,
)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(exist_ok=True)


class NotebookCreate(BaseModel):
    title: str
    notebook_type: str


class MoveCellPayload(BaseModel):
    direction: str  # "up" | "down"


class MoveCellWeekPayload(BaseModel):
    target_week: int


class CellOrderPayload(BaseModel):
    cell_id: str
    week: int
    order_index: int


class RenameNotebookPayload(BaseModel):
    title: str


class SummarizeCellPayload(BaseModel):
    content: str


def get_current_week_from_tasks(notebook_id: str, db):
    """
    Returns the current active week for a notebook.

    Rules:
    - The first week that has at least one 'pending' task is the current week.
    - If all tasks are completed, return the highest week number.
    - If no tasks exist, default to week 1.
    """

    rows = db.execute(
        """
        SELECT week, status
        FROM tasks
        WHERE notebook_id = ?
        ORDER BY week ASC
        """,
        (notebook_id,),
    ).fetchall()

    if not rows:
        return 1  # fallback safety

    weeks = {}
    for row in rows:
        weeks.setdefault(row["week"], []).append(row["status"])

    # Find first week with pending tasks
    for week in sorted(weeks.keys()):
        if any(status == "pending" for status in weeks[week]):
            return week

    # All tasks done → return last week
    return max(weeks.keys())


# NOTEBOOK APIs


@router.post("/")
def create_notebook(payload: NotebookCreate, user_id: int, db=Depends(get_db)):
    notebook_id = str(uuid.uuid4())
    # db.execute("BEGIN IMMEDIATE")

    db.execute(
        """
        INSERT INTO notebooks (notebook_id, user_id, title, notebook_type, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            notebook_id,
            user_id,
            payload.title,
            payload.notebook_type,
            "A general-purpose notebook for free-form notes and ideas.",
            int(time.time()),
        ),
    )
    db.commit()

    return {
        "notebook_id": notebook_id,
        "title": payload.title,
        "notebook_type": payload.notebook_type,
    }


@router.get("/")
def get_notebooks(user_id: int, db=Depends(get_db)):
    cursor = db.execute(
        "SELECT * FROM notebooks WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    )
    return cursor.fetchall()


@router.get("/{notebook_id}")
def get_notebook(notebook_id: str, user_id: int, db=Depends(get_db)):
    cursor = db.execute(
        """
        SELECT * FROM notebooks
        WHERE notebook_id = ? AND user_id = ?
        """,
        (notebook_id, user_id),
    )
    notebook = cursor.fetchone()

    if not notebook:
        return {"error": "Notebook not found"}

    return notebook


@router.patch("/{notebook_id}/rename")
def rename_notebook(
    notebook_id: str, payload: RenameNotebookPayload, user_id: str, db=Depends(get_db)
):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    result = db.execute(
        """
        UPDATE notebooks
        SET title = ?, updated_at = ?
        WHERE notebook_id = ? AND user_id = ?
        """,
        (payload.title.strip(), int(time.time()), notebook_id, user_id),
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Notebook not found")

    db.commit()
    return {"status": "renamed"}


# CELL APIs


@router.get("/{notebook_id}/cells")
def get_cells(notebook_id: str, user_id: int, db=Depends(get_db)):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    rows = db.execute(
        """
        SELECT
            cell_id,
            order_index,
            week,
            user_content,
            ai_content
        FROM cells
        WHERE notebook_id = ?
        ORDER BY week, order_index
        """,
        (notebook_id,),
    ).fetchall()

    return [
        {
            "cell_id": row["cell_id"],
            "order_index": row["order_index"],
            "week": row["week"],
            "content": row["user_content"] or "",
            "ai_summary": row["ai_content"],
        }
        for row in rows
    ]


@router.post("/{notebook_id}/cells")
def add_cell(notebook_id: str, user_id: int, db=Depends(get_db)):
    # db.execute("BEGIN IMMEDIATE")

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    current_week = get_current_week_from_tasks(notebook_id, db)

    order_index = db.execute(
        """
    SELECT COUNT(*)
    FROM cells
    WHERE notebook_id = ? AND week = ?
    """,
        (notebook_id, current_week),
    ).fetchone()[0]

    cell_id = str(uuid.uuid4())

    db.execute(
        """
        INSERT INTO cells (cell_id, notebook_id, user_content, order_index, week)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cell_id, notebook_id, "", order_index, current_week),
    )

    db.commit()
    return {"cell_id": cell_id, "order_index": order_index, "week": current_week}


@router.put("/{notebook_id}/cells/{cell_id}")
def update_cell(
    cell_id: str, notebook_id: str, content: str = Body(...), db=Depends(get_db)
):
    # db.execute("BEGIN IMMEDIATE")

    db.execute(
        "UPDATE cells SET user_content = ? WHERE cell_id = ? AND notebook_id = ?",
        (content, cell_id, notebook_id),
    )
    db.commit()

    return {"status": "updated"}


@router.delete("/{notebook_id}/cells/{cell_id}")
def delete_cell(notebook_id: str, cell_id: str, user_id: int, db=Depends(get_db)):
    db.execute("BEGIN")

    # Ownership check
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    # Fetch cell info ONCE (before delete)
    cell = db.execute(
        """
        SELECT order_index, week
        FROM cells
        WHERE cell_id = ? AND notebook_id = ?
        """,
        (cell_id, notebook_id),
    ).fetchone()

    if not cell:
        return {"error": "Cell not found"}

    order_index = cell["order_index"]
    week = cell["week"]

    # Delete cell
    db.execute(
        "DELETE FROM cells WHERE cell_id = ? AND notebook_id = ?",
        (cell_id, notebook_id),
    )

    # Shift remaining cells IN THE SAME WEEK ONLY
    db.execute(
        """
        UPDATE cells
        SET order_index = order_index - 1
        WHERE notebook_id = ?
          AND week = ?
          AND order_index > ?
        """,
        (notebook_id, week, order_index),
    )

    db.commit()
    return {"status": "deleted"}


@router.post("/{notebook_id}/cells/{cell_id}/move")
def move_cell(
    notebook_id: str,
    cell_id: str,
    payload: MoveCellPayload,
    user_id: int,
    db=Depends(get_db),
):
    db.execute("BEGIN")

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    cell = db.execute(
        "SELECT order_index FROM cells WHERE cell_id = ? AND notebook_id = ?",
        (cell_id, notebook_id),
    ).fetchone()

    if not cell:
        return {"error": "Cell not found"}

    current_index = cell["order_index"]
    target_index = current_index - 1 if payload.direction == "up" else current_index + 1

    cell = db.execute(
        "SELECT order_index, week FROM cells WHERE cell_id = ? AND notebook_id = ?",
        (cell_id, notebook_id),
    ).fetchone()

    week = cell["week"]
    # current_index = cell["order_index"]

    target = db.execute(
        """
        SELECT cell_id FROM cells
        WHERE notebook_id = ? AND week = ? AND order_index = ?
        """,
        (notebook_id, week, target_index),
    ).fetchone()

    if not target:
        return {"status": "edge"}  # top or bottom

    # swap
    db.execute(
        "UPDATE cells SET order_index = ? WHERE cell_id = ?",
        (target_index, cell_id),
    )
    db.execute(
        "UPDATE cells SET order_index = ? WHERE cell_id = ?",
        (current_index, target["cell_id"]),
    )

    db.commit()
    return {"status": "moved"}


@router.post("/{notebook_id}/cells/{cell_id}/move-week")
def move_cell_to_week(
    notebook_id: str,
    cell_id: str,
    payload: MoveCellWeekPayload,
    user_id: int,
    db=Depends(get_db),
):
    db.execute("BEGIN")

    # Ownership check
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    # Fetch cell
    cell = db.execute(
        """
        SELECT week, order_index
        FROM cells
        WHERE cell_id = ? AND notebook_id = ?
        """,
        (cell_id, notebook_id),
    ).fetchone()

    if not cell:
        return {"error": "Cell not found"}

    current_week = cell["week"]
    current_index = cell["order_index"]
    target_week = payload.target_week

    if current_week == target_week:
        return {"status": "no-op"}

    # Close gap in old week
    db.execute(
        """
        UPDATE cells
        SET order_index = order_index - 1
        WHERE notebook_id = ?
          AND week = ?
          AND order_index > ?
        """,
        (notebook_id, current_week, current_index),
    )

    # Compute new index in target week
    new_index = db.execute(
        """
        SELECT COUNT(*)
        FROM cells
        WHERE notebook_id = ? AND week = ?
        """,
        (notebook_id, target_week),
    ).fetchone()[0]

    # Move cell
    db.execute(
        """
        UPDATE cells
        SET week = ?, order_index = ?
        WHERE cell_id = ?
        """,
        (target_week, new_index, cell_id),
    )

    db.commit()
    return {"status": "moved", "week": target_week}


@router.post("/{notebook_id}/cells/{cell_id}/summarize")
def summarize_cell(
    notebook_id: str,
    cell_id: str,
    payload: SummarizeCellPayload,
    user_id: int,
    db=Depends(get_db),
):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Empty content")

    summary = generate_summary_with_ollama(payload.content)

    db.execute(
        """
        UPDATE cells
        SET ai_content = ?
        WHERE cell_id = ? AND notebook_id = ?
        """,
        (summary, cell_id, notebook_id),
    )
    db.commit()

    return {
        "cell_id": cell_id,
        "summary": summary,
    }


@router.delete("/{notebook_id}/cells/{cell_id}/summary")
def delete_cell_summary(
    notebook_id: str,
    cell_id: str,
    user_id: int,
    db=Depends(get_db),
):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db.execute(
        """
        UPDATE cells
        SET ai_content = NULL
        WHERE cell_id = ? AND notebook_id = ?
        """,
        (cell_id, notebook_id),
    )
    db.commit()

    return {"status": "deleted"}


@router.post("/{notebook_id}/cells/{cell_id}/attachments")
def upload_attachment(
    notebook_id: str,
    cell_id: str,
    file: UploadFile = File(...),
    user_id: int = None,
    db=Depends(get_db),
):
    # Ownership check
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Ensure cell exists
    cell = db.execute(
        "SELECT 1 FROM cells WHERE cell_id = ? AND notebook_id = ?",
        (cell_id, notebook_id),
    ).fetchone()

    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    attachment_id = str(uuid.uuid4())

    # Create directory: uploads/{notebook_id}/{cell_id}
    cell_dir = UPLOAD_ROOT / notebook_id / cell_id
    cell_dir.mkdir(parents=True, exist_ok=True)

    file_path = cell_dir / file.filename

    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Determine type
    ext = file.filename.lower().split(".")[-1]
    if ext in ["pdf"]:
        file_type = "pdf"
    elif ext in ["png", "jpg", "jpeg", "webp"]:
        file_type = "image"
    else:
        file_type = "other"

    db.execute(
        """
        INSERT INTO cell_attachments (
            attachment_id, cell_id, file_name, file_type, storage_path, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            attachment_id,
            cell_id,
            file.filename,
            file_type,
            str(file_path),
            int(time.time()),
        ),
    )

    db.commit()

    return {
        "attachment_id": attachment_id,
        "file_name": file.filename,
        "file_type": file_type,
        "url": f"/uploads/{notebook_id}/{cell_id}/{file.filename}",
    }


@router.get("/{notebook_id}/cells/{cell_id}/attachments")
def get_attachments(
    notebook_id: str,
    cell_id: str,
    user_id: int,
    db=Depends(get_db),
):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    rows = db.execute(
        """
        SELECT attachment_id, file_name, file_type, storage_path
        FROM cell_attachments
        WHERE cell_id = ?
        ORDER BY created_at DESC
        """,
        (cell_id,),
    ).fetchall()

    results = []
    for row in rows:
        file_name = row["file_name"]
        results.append(
            {
                "attachment_id": row["attachment_id"],
                "file_name": file_name,
                "file_type": row["file_type"],
                "url": f"/uploads/{notebook_id}/{cell_id}/{file_name}",
            }
        )

    return results


@router.delete("/{notebook_id}/cells/{cell_id}/attachments/{attachment_id}")
def delete_attachment(
    notebook_id: str,
    cell_id: str,
    attachment_id: str,
    user_id: int,
    db=Depends(get_db),
):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=403, detail="Unauthorized")

    row = db.execute(
        """
        SELECT file_name, storage_path
        FROM cell_attachments
        WHERE attachment_id = ? AND cell_id = ?
        """,
        (attachment_id, cell_id),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Delete file from disk
    try:
        os.remove(row["storage_path"])
    except FileNotFoundError:
        pass

    db.execute(
        "DELETE FROM cell_attachments WHERE attachment_id = ?",
        (attachment_id,),
    )

    db.commit()

    return {"status": "deleted"}


@router.post("/educational")
def create_educational_notebook(
    payload: LearningPlanRequest, user_id: int, db=Depends(get_db)
):
    notebook_id = str(uuid.uuid4())
    created_at = int(time.time())

    # Create notebook immediately
    db.execute(
        """
        INSERT INTO notebooks (
            notebook_id, user_id, title, notebook_type, description, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notebook_id,
            user_id,
            payload.topic,
            "educational",
            generate_notebook_description(payload.topic),
            created_at,
            created_at,
        ),
    )
    db.commit()

    # Run AI in background
    def run_ai():
        from bitnote.services.educational_ai.learning_plan_service import (
            generate_learning_plan,
        )

        local_db = get_db()
        cursor = local_db.cursor()

        learning_plan = generate_learning_plan(payload)

        cursor.execute(
            """
            INSERT INTO educational_metadata (
                notebook_id, learning_goal, course_topic, syllabus, roadmap, progress, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                notebook_id,
                learning_plan.learning_goal,
                payload.course_topic,
                json.dumps(learning_plan.syllabus),
                json.dumps([week.dict() for week in learning_plan.roadmap]),
                0.0,
            ),
        )

        now = int(time.time())
        for week in learning_plan.roadmap:
            order_index = 0
            for day in week.days:
                cursor.execute(
                    """
                    INSERT INTO tasks(task_id, notebook_id, week, day, order_index, task_description, status, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()),
                        notebook_id,
                        week.week,
                        day.day,
                        order_index,
                        day.task,
                        "pending",
                        now,
                        now,
                    ),
                )
                order_index += 1

        local_db.commit()

    threading.Thread(target=run_ai, daemon=True).start()

    # RETURN IMMEDIATELY
    return {"notebook_id": notebook_id}


@router.get("/{notebook_id}/tasks")
def get_tasks(notebook_id: str, user_id: str, db=Depends(get_db)):
    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    rows = db.execute(
        """
        SELECT task_id, week, day, task_description, status
        FROM tasks
        WHERE notebook_id = ?
        ORDER BY week, day, order_index
    """,
        (notebook_id,),
    ).fetchall()

    return [dict(row) for row in rows]


@router.put("/tasks/{task_id}")
def update_task_status(task_id: str, payload: dict, user_id: int, db=Depends(get_db)):
    status = payload.get("status")

    if status not in ("pending", "done"):
        return {"error": "Invalid status"}

    # Ownership check
    row = db.execute(
        """
        SELECT t.task_id
        FROM tasks t
        JOIN notebooks n ON t.notebook_id = n.notebook_id
        WHERE t.task_id = ? AND n.user_id = ?
    """,
        (task_id, user_id),
    ).fetchone()

    if not row:
        return {"error": "Unauthorized"}

    now = int(time.time())

    db.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = ?
        WHERE task_id = ?
    """,
        (status, now, task_id),
    )

    db.commit()

    return {"success": True}


@router.post("/{notebook_id}/cells/reorder")
def reorder_cells(
    notebook_id: str, payload: list[CellOrderPayload], user_id: int, db=Depends(get_db)
):
    db.execute("BEGIN")

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        return {"error": "Unauthorized"}

    for item in payload:
        db.execute(
            """
            UPDATE cells
            SET week = ?, order_index = ?
            WHERE cell_id = ? AND notebook_id = ?
            """,
            (item.week, item.order_index, item.cell_id, notebook_id),
        )

    db.commit()
    return {"status": "ok"}


@router.delete("/{notebook_id}")
def delete_notebook(notebook_id: str, user_id: str, db=Depends(get_db)):
    db.execute("BEGIN")

    owner = db.execute(
        "SELECT 1 FROM notebooks WHERE notebook_id = ? AND user_id = ?",
        (notebook_id, user_id),
    ).fetchone()

    if not owner:
        raise HTTPException(status_code=400, detail="Notebook not found")

    db.execute("DELETE FROM notebooks WHERE notebook_id = ?", (notebook_id,))
    db.commit()

    return {"status": "deleted"}
