from flask import jsonify


def success_response(
    data=None,
    message=None
):

    response = {

        "status":
            "success"
    }


    if message is not None:

        response["message"] = message


    if data is not None:

        response["data"] = data


    return jsonify(response)


def error_response(
    message,
    status_code=400
):

    return jsonify({

        "status":
            "error",

        "message":
            message

    }), status_code
