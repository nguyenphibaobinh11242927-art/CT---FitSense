"""Compatibility entrypoint for the main FitSense UI (SCRUM-17)."""
from src.exercise_library_view import render_exercise_library_view


def render_library_view():
    """Keep the existing app.py API while the implementation moves to its own UI module."""
    return render_exercise_library_view()
