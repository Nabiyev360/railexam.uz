import requests as req
from .models import Settings


def get_setting_value(key):
    return Settings.objects.get(key=key).value


def refresh_token():
    login_url = "https://api-exodim.railway.uz/api/auth/login"
    exodim_login = get_setting_value('exodim_login')
    exodim_password = get_setting_value('exodim_password')

    response = req.post(
        url=login_url,
        data={
            "email": exodim_login,
            "password": exodim_password
        }
    )

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception("Failed to refresh token: {}".format(response.text))


def check_employee(pin):
    access_token = get_setting_value('access_token')
    url = f'https://api-exodim.railway.uz/api/v2/commands/check-worker?pin={pin}'
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = req.get(url=url, headers=headers)
    if response.status_code != 200:
        new_token = refresh_token()
        access_token_setting = Settings.objects.get(key='access_token')
        access_token_setting.value = new_token
        access_token_setting.save()

        headers["Authorization"] = f"Bearer {new_token}"
        response = req.get(url=url, headers=headers)

    return response
