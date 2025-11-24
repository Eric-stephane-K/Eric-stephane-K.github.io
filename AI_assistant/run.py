from app import create_app

app = create_app()

if __name__ == "__main__":
    app.logger.warning("Starting SongWish AI Shopping Assistant...")
    app.run(debug=app.config.get('DEBUG', False), port=5000)
