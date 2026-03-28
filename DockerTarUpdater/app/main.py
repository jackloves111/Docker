from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    config = app.config['APP_CONFIG']
    socketio.run(app,
                host=config['app']['host'],
                port=config['app']['port'],
                debug=config['app']['debug'])
