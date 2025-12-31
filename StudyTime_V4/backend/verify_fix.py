"""
Quick verification script to test the database fix
Run with: python verify_fix.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys

print("Testing SQLAlchemy 2.0 text() fix...")
print("=" * 50)

# Create engine
DATABASE_URL = "sqlite:///studytime.db"
engine = create_engine(DATABASE_URL, echo=False)

# Create session
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Test 1: Execute with text()
    print("\n1. Testing db.execute(text('SELECT 1'))...")
    result = db.execute(text("SELECT 1"))
    print("   ✓ SUCCESS: Raw SQL with text() works!")
    
    # Test 2: Try without text() (should fail)
    print("\n2. Testing db.execute('SELECT 1') without text()...")
    try:
        result = db.execute("SELECT 1")
        print("   ✗ UNEXPECTED: Should have failed!")
    except Exception as e:
        print(f"   ✓ Expected error: {type(e).__name__}")
        print(f"   (This confirms SQLAlchemy 2.0 requires text())")
    
    # Test 3: Test database tables exist
    print("\n3. Testing database tables...")
    from models import Base, Course, Task, Break, Job, Commute
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Query counts
    tables_info = {
        "courses": db.query(Course).count(),
        "tasks": db.query(Task).count(),
        "breaks": db.query(Break).count(),
        "jobs": db.query(Job).count(),
        "commutes": db.query(Commute).count()
    }
    
    print("   ✓ SUCCESS: All tables accessible!")
    for table, count in tables_info.items():
        print(f"     - {table}: {count} records")
    
    print("\n" + "=" * 50)
    print("✓ All tests passed! Database is working correctly.")
    print("=" * 50)
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
finally:
    db.close()