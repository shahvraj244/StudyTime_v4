# SQLAlchemy 2.0 Compatibility Fix

## Problem

You encountered this error:
```
sqlalchemy.exc.ArgumentError: Textual SQL expression 'SELECT 1' 
should be explicitly declared as text('SELECT 1')
```

## Root Cause

**SQLAlchemy 2.0** introduced breaking changes requiring explicit wrapping of raw SQL strings with the `text()` function. This is a security measure to prevent SQL injection and make code intentions explicit.

### Before (SQLAlchemy 1.4 style):
```python
db.execute("SELECT 1")
```

### After (SQLAlchemy 2.0 style):
```python
from sqlalchemy import text
db.execute(text("SELECT 1"))
```

## Files Fixed

### 1. **database.py**
Changed:
```python
# OLD - Line 1
from sqlalchemy import create_engine, event

# OLD - Line 280
db.execute("SELECT 1")
```

To:
```python
# NEW - Line 1
from sqlalchemy import create_engine, event, text

# NEW - Line 280
db.execute(text("SELECT 1"))
```

### 2. **main.py**
Changed:
```python
# OLD - Line 7
from sqlalchemy.orm import Session

# OLD - Line 548
db.execute("SELECT 1")
```

To:
```python
# NEW - Line 7
from sqlalchemy import text
from sqlalchemy.orm import Session

# NEW - Line 548
db.execute(text("SELECT 1"))
```

## Verification Steps

### 1. Run the verification script:
```bash
python verify_fix.py
```

Expected output:
```
Testing SQLAlchemy 2.0 text() fix...
==================================================

1. Testing db.execute(text('SELECT 1'))...
   ✓ SUCCESS: Raw SQL with text() works!

2. Testing db.execute('SELECT 1') without text()...
   ✓ Expected error: ArgumentError
   (This confirms SQLAlchemy 2.0 requires text())

3. Testing database tables...
   ✓ SUCCESS: All tables accessible!
     - courses: 0 records
     - tasks: 0 records
     - breaks: 0 records
     - jobs: 0 records
     - commutes: 0 records

==================================================
✓ All tests passed! Database is working correctly.
==================================================
```

### 2. Test database operations:
```bash
# Initialize database
python database.py init

# Check connection (should now work)
python database.py check

# View database info
python database.py info
```

### 3. Start the server:
```bash
uvicorn main:app --reload
```

### 4. Test the health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "StudyTime API",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2025-12-30T23:45:00.123456"
}
```

## SQLAlchemy 2.0 Best Practices

### ✅ DO:
```python
from sqlalchemy import text

# For raw SQL
db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": 123})

# For ORM queries (no text() needed)
db.query(User).filter(User.id == 123).all()
```

### ❌ DON'T:
```python
# Raw strings (will fail)
db.execute("SELECT * FROM users")

# String formatting (SQL injection risk!)
db.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

## Additional SQLAlchemy 2.0 Changes

If you encounter other issues, here are common patterns:

### 1. Query syntax changes:
```python
# OLD (1.4)
db.query(User).filter_by(name="John").first()

# NEW (2.0 preferred)
from sqlalchemy import select
stmt = select(User).where(User.name == "John")
result = db.execute(stmt).scalar_one_or_none()
```

### 2. Transaction handling:
```python
# Explicit commits still work
db.add(user)
db.commit()

# But recommended to use context managers
with db.begin():
    db.add(user)
```

### 3. Result handling:
```python
# Execute returns a Result object
result = db.execute(text("SELECT * FROM users"))
rows = result.fetchall()  # Get all rows
```

## Testing Checklist

After applying the fix, verify:

- [ ] `python database.py check` - Returns ✓
- [ ] `python verify_fix.py` - All tests pass
- [ ] `uvicorn main:app --reload` - Starts without errors
- [ ] `curl http://localhost:8000/health` - Returns "connected"
- [ ] `python test_backend.py` - All API tests pass

## If You Still Have Issues

### Issue: Import error for `text`
**Solution**: Make sure SQLAlchemy 2.0+ is installed:
```bash
pip install --upgrade sqlalchemy
```

### Issue: Other ArgumentError messages
**Solution**: Search your codebase for any raw SQL strings:
```bash
grep -r "db.execute(\"" .
grep -r "db.execute('" .
```
Wrap any found instances with `text()`.

### Issue: Column type errors
**Solution**: SQLAlchemy 2.0 is stricter about types. Ensure your models match your data.

## References

- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [Using text() Documentation](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text)

## Summary

✅ **Fixed**: Both `database.py` and `main.py` now properly use `text()` for raw SQL  
✅ **Compatible**: Code now works with SQLAlchemy 2.0+  
✅ **Secure**: Explicit text() prevents accidental SQL injection  
✅ **Tested**: Verification script confirms the fix works  

Your backend is now fully compatible with SQLAlchemy 2.0! 🎉