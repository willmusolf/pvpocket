# Pokemon TCG Pocket App

A web application for managing Pokemon Trading Card Game collections, building decks, and simulating battles.

## Features

- Card collection management
- Deck building and editing
- Battle simulation
- Meta game analysis
- User authentication

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python run.py
   ```

That's it! The app will automatically:
- Generate a secure secret key
- Create necessary directories and files
- Set up the database if it doesn't exist

## Security Notes

This repository is configured to exclude sensitive information:
- User data and passwords are not stored in the repository
- Database files are excluded from Git
- Secret keys are auto-generated and not committed

## Project Structure

- `/app` - Flask application and routes
- `/templates` - HTML templates
- `/images` - Card and energy type images
- `/data` - User data storage
- `/decks` - Saved deck configurations
