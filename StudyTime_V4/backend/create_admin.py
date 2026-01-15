"""
Admin Account Setup Script
Run this once to create admin account and migrate existing data
"""

from database import get_db_context, init_db
from models import User, Course, Task, Break, Job, Commute, UserPreferences, ScheduledEvent
from auth import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_and_migrate():
    """Create admin account and assign all existing data to it"""
    
    with get_db_context() as db:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == "admin@studytime.com").first()
        
        if admin:
            logger.info(f"✓ Admin account already exists: {admin.email}")
            admin_id = admin.id
        else:
            # Create admin account
            admin = User(
                email="admin@studytime.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),  # Change this password!
                full_name="StudyTime Administrator",
                is_admin=True,
                is_active=True
            )
            
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            admin_id = admin.id
            
            logger.info("=" * 60)
            logger.info("✓ ADMIN ACCOUNT CREATED")
            logger.info(f"  Email: admin@studytime.com")
            logger.info(f"  Password: admin123")
            logger.info(f"  ⚠️  PLEASE CHANGE THIS PASSWORD AFTER FIRST LOGIN!")
            logger.info("=" * 60)
        
        # Migrate existing data to admin account
        models_to_migrate = [
            (Course, "courses"),
            (Task, "tasks"),
            (Break, "breaks"),
            (Job, "jobs"),
            (Commute, "commutes"),
            (UserPreferences, "preferences"),
            (ScheduledEvent, "scheduled events")
        ]
        
        for model, name in models_to_migrate:
            # Find records without user_id
            records = db.query(model).filter(model.user_id == None).all()
            
            if records:
                for record in records:
                    record.user_id = admin_id
                
                db.commit()
                logger.info(f"✓ Migrated {len(records)} {name} to admin account")
            else:
                logger.info(f"  No {name} to migrate")
        
        logger.info("\n✅ Migration complete! All existing data now belongs to admin account.")
        logger.info("   You can now login with admin@studytime.com / admin123")

if __name__ == "__main__":
    logger.info("StudyTime Admin Account Setup")
    logger.info("=" * 60)
    
    # Initialize database
    init_db()
    
    # Create admin and migrate data
    create_admin_and_migrate()