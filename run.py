from app import create_app

# Use 'development', 'production', or 'testing'
app = create_app('development')

if __name__ == '__main__':
    app.run()