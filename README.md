# Digital SAT Mock-Test Platform

A web-based Digital SAT practice platform built with Python and Flask.

## Project Overview

I am developing this platform to help students prepare for the Digital SAT through online practice tests. The project is also helping me develop practical skills in Python, web development, database management, and software engineering.

## Current Features

- User registration and login
- Mock-test creation and management
- Question management for administrators
- Multiple-choice questions with answer choices and explanations
- Saving test answers and recording test attempts
- Test results and score history

## Technologies

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- HTML, CSS, and JavaScript

## Run Locally

1. Install Python.
2. Clone this repository.
3. Open a terminal in the project folder.
4. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Start the application:

   ```bash
   python -m flask --app "website:create_app" run --debug
   ```

6. Open `http://127.0.0.1:5000` in your browser.

## Development Status

This project is under active development. Timed Digital SAT modules, a more realistic test-taking interface, and adaptive module routing are planned improvements and should not be considered completed features yet.

## Purpose

My goal is to build a useful educational tool while strengthening my programming and problem-solving skills through hands-on development.

## Security and Data

The local SQLite database, uploaded question images, environment files, and Python cache files are excluded from the repository. A fresh local setup may require creating an account and adding questions through the application.
