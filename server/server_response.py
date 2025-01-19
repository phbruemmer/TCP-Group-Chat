
"""
codes:
1: normal message
2: change server
3: Not Found
4: Server Error
5: close connection
"""


def generate_response(code, host, **kwargs) -> dict:
    response = {
        'code': code,
        'host': host,
    }

    for keyword in kwargs:
        response[keyword] = kwargs[keyword]

    return response


if __name__ == "__main__":
    response = generate_response(2, '192.168.115.200', connection=['192.168.115.200', 8000])
    print(response)
