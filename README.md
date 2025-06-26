# Pokemon TCG Pocket App

A web application for managing Pokemon Trading Card Game collections, building decks, and simulating battles.

## Features

- Card collection management
- Deck building and editing
- Battle simulation
- Meta game analysis
- User authentication

## Security Notes

This repository is configured to exclude sensitive information:
- User data and passwords are not stored at all due to Google OAuth
- Secret keys are auto-generated and not committed

## Project Structure

- `/app` - Flask application and routes
- `/templates` - HTML templates