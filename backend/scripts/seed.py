import os
import sys
import uuid
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend root to sys.path so app modules resolve cleanly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.task import Task


def seed_database():
    """Repeatable, idempotent database seeding script."""
    db = SessionLocal()
    try:
        print("[1/3] Ensuring seed user exists...")
        user = db.query(User).filter_by(email="seed.user@taskflow.dev").first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="seed.user@taskflow.dev",
                hashed_password="pbkdf2_sha256$mockhash$safe_seed_password_123",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"      Created user: {user.email} (ID: {user.id})")
        else:
            print(f"      User already exists: {user.email} (ID: {user.id})")

        print("[2/3] Ensuring 3 projects exist...")
        project_names = ["Project Alpha", "Project Beta", "Project Gamma"]
        projects = []
        for name in project_names:
            proj = db.query(Project).filter_by(user_id=user.id, name=name).first()
            if not proj:
                proj = Project(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    name=name,
                    description=f"Auto-generated seed project: {name}",
                )
                db.add(proj)
                db.commit()
                db.refresh(proj)
                print(f"      Created project: {name} (ID: {proj.id})")
            else:
                print(f"      Project already exists: {name} (ID: {proj.id})")
            projects.append(proj)

        print("[3/3] Checking task count...")
        existing_count = db.query(Task).filter_by(user_id=user.id).count()
        target_count = 10000

        if existing_count >= target_count:
            print(f"      Database already contains {existing_count} tasks. Skipping generation.")
            return

        needed = target_count - existing_count
        print(f"      Generating {needed} tasks in bulk...")

        statuses = ["todo", "in_progress", "done"]
        priorities = ["low", "medium", "high"]
        verbs = ["Refactor", "Implement", "Audit", "Debug", "Design", "Benchmark", "Deploy", "Test"]
        nouns = ["Authentication", "CORS Middleware", "Task Filtering", "Database Index", "JWT Rotation", "Worker Queue", "Healthcheck"]

        batch_size = 2000
        tasks_batch = []
        now = datetime.now(timezone.utc)

        for i in range(needed):
            task_num = existing_count + i + 1
            proj = random.choice(projects)
            task = Task(
                id=uuid.uuid4(),
                user_id=user.id,
                project_id=proj.id,
                title=f"{random.choice(verbs)} {random.choice(nouns)} #{task_num}",
                description=f"Automated workload item #{task_num} assigned to {proj.name}",
                status=random.choice(statuses),
                priority=random.choice(priorities),
                due_date=now + timedelta(days=random.randint(1, 45)),
                created_at=now,
                updated_at=now,
            )
            tasks_batch.append(task)

            if len(tasks_batch) >= batch_size:
                db.add_all(tasks_batch)
                db.commit()
                print(f"      Committed batch: {task_num}/{target_count} tasks...")
                tasks_batch = []

        if tasks_batch:
            db.add_all(tasks_batch)
            db.commit()

        total = db.query(Task).filter_by(user_id=user.id).count()
        print(f"[Done] Total tasks in database for user: {total}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
