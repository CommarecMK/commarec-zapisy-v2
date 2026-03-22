"""
run.py — vstupní bod aplikace.
Railway/gunicorn volá: gunicorn run:app
"""
import os
import sys
import traceback

print("=== STARTUP BEGIN ===", flush=True)
print(f"Python: {sys.version}", flush=True)
print(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}", flush=True)
print(f"ANTHROPIC_API_KEY set: {'ANTHROPIC_API_KEY' in os.environ}", flush=True)

try:
    print("Importing create_app...", flush=True)
    from app import create_app
    print("create_app imported OK", flush=True)
except Exception as e:
    print(f"IMPORT ERROR: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

try:
    print("Calling create_app()...", flush=True)
    app = create_app()
    print("create_app() OK", flush=True)
    print("=== STARTUP COMPLETE ===", flush=True)
except Exception as e:
    print(f"CREATE_APP ERROR: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
