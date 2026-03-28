from flask import jsonify

def success(data=None, message='Success'):
    response = {'success': True, 'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response)

def error(message='Error', code=400, data=None):
    response = {'success': False, 'message': message, 'code': code}
    if data is not None:
        response['data'] = data
    return jsonify(response)
