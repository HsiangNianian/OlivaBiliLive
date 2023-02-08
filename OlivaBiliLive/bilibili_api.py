import OlivOS
import OlivaBiliLive

from aiohttp import cookiejar
from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientResponseError
import qrcode
import aiohttp
import asyncio
import time, os
from functools import wraps
from qrcode.main import QRCode

QRCODE_REQUEST_URL = 'http://passport.bilibili.com/qrcode/getLoginUrl'
CHECK_LOGIN_RESULT = 'http://passport.bilibili.com/qrcode/getLoginInfo'
SEND_URL = 'https://api.live.bilibili.com/msg/send'
MUTE_USER_URL = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddSilentUser'
ROOM_SLIENT_URL = 'https://api.live.bilibili.com/xlive/web-room/v1/banned/RoomSilent'
ADD_BADWORD_URL = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddShieldKeyword'
DEL_BADWORD_URL = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/DelShieldKeyword'

user_cookies = cookiejar.CookieJar()

def logg(msg:str,level=2):
    OlivaBiliLive.main.GlobalProc.log(level,f"[OlivaBiliLive] : {msg}")

"""
Bilibili Client Operation

"""
async def login(session: ClientSession): # -> bool:
    if get_cookies('bili_jct') != None:
        logg("已使用上次登录配置登录。")

        return True
    try:
        
        res = await _get(session, QRCODE_REQUEST_URL)

        ts = res['ts']
        outdated = ts + 180 * 1000 # 180 秒後逾時
        authKey = res['data']['oauthKey']

        url = res['data']['url']
        qr = qrcode.QRCode()

        logg("请扫描下方二维码登录... 或者到根目录(也就是OlivOS.exe所在目录)寻找 OlivaBiliLive_qrcode.png)")

        qr.add_data(url)
        qr.print_ascii(invert=True)
        qr.make_image().save('OlivaBiliLive_qrcode.png')

        os.startfile('OlivaBiliLive_qrcode.png') # Linux方案: subprocess.call(["xdg-open",file_path])
        
        while True:

            await asyncio.sleep(5)

            if time.time() > outdated:

                logg("已超时。")

                return False # 登入失敗

            res = await _post(session, CHECK_LOGIN_RESULT, oauthKey=authKey)

            if res['status']:
                logg('登入成功。')
                return True
            else:
                code = res['data']
                if code in [-1, -2]:
                    logg(f'登入失敗: {res["message"]}')
                    return False

    except ClientResponseError as e:
        logg(f'请求时出现错误: {e}')
        return False
    finally:
        os.remove('OlivaBiliLive_qrcode.png')


async def send_danmu(**fields) -> bool:
    token = get_cookies("bili_jct")
    async with ClientSession(cookie_jar=user_cookies) as session:
        try:
            res = await _post(session, SEND_URL,
                rnd=time.time(),
                csrf=token,
                csrf_token=token,
                **fields
            )
            return 'data' in res
        except Exception as e:
            logg(f'发送弹幕时出现错误: {e}')
            return False

def get_cookies(name: str) -> any:
    return next(
        (cookie.value for cookie in user_cookies if cookie.key == name), None
    )

async def mute_user(tuid: int, roomid: int) -> bool:
    token = get_cookies('bili_jct')
    async with ClientSession(cookie_jar=user_cookies) as session:
        try:
            res = await _post(session, MUTE_USER_URL,
                csrf=token,
                csrf_token=token,
                visit_id='',
                mobile_app='web',
                tuid=str(tuid),
                room_id=str(roomid)
            )
            return res['code'] == 0
        except Exception as e:
            logg(f'禁言时出现错误: {e}')
            return False

async def room_slient(roomid: int, slientType: str, level: int, minute: int) -> bool:

    type_availables = ['off', 'medal', 'member', 'level']
    if slientType not in type_availables:
        logg(f'未知的禁言类型: {slientType} ({type_availables})')
        return False

    minute_available = [0, 30, 60]
    if minute not in minute_available:
        logg(f'未知的静音时间: {minute} ({minute_available})')
        return False

    token = get_cookies('bili_jct')
    async with ClientSession(cookie_jar=user_cookies) as session:
        try:
            res = await _post(
                session,
                ROOM_SLIENT_URL,
                csrf=token,
                csrf_token=token,
                visit_id='',
                room_id=str(roomid),
                type=slientType,
                minute=str(minute),
                level=str(level),
            )
            return res['code'] == 0
        except Exception as e:
            logg(f'房间静音时出现错误: {e}')
            return False

async def add_badword(roomid: int, keyword: str) -> bool:
    token = get_cookies('bili_jct')
    async with ClientSession(cookie_jar=user_cookies) as session:
        try:
            res = await _post(session, ADD_BADWORD_URL,
                csrf=token,
                csrf_token=token,
                visit_id='',
                room_id=str(roomid),
                keyword=keyword
            )
            return res['code'] == 0
        except Exception as e:
            logg(f'添加屏蔽字时出现错误: {e}')
            return False

async def remove_badword(roomid: int, keyword: str) -> bool:
    token = get_cookies('bili_jct')
    async with ClientSession(cookie_jar=user_cookies) as session:
        try:
            res = await _post(session, DEL_BADWORD_URL,
                csrf=token,
                csrf_token=token,
                visit_id='',
                room_id=str(roomid),
                keyword=keyword
            )
            return res['code'] == 0
        except Exception as e:
            logg(f'删除屏蔽字时出现错误: {e}')
            return False

def logout():
    user_cookies.clear()

"""
Http Request

"""

async def _get(session: ClientSession, url: str):
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()
        logg(data)
        if 'code' in data and data['code'] != 0:
            raise Exception(data['message'] if 'message' in data else data['code'])
        return data


async def _post(session: ClientSession, url: str, **data):
    form = aiohttp.FormData()
    for (k, v) in data.items():
        form.add_field(k, v)
    logg(f'正在发送 POST 请求: {url}, 内容: {data}')
    async with session.post(url, data=form) as resp:
        resp.raise_for_status()
        data = await resp.json()
        logg(data)
        if 'code' in data and data['code'] != 0:
            raise Exception(data['message'] if 'message' in data else data['code'])
        return data


if __name__ == '__main__':
    session = ClientSession(cookies={'a': 1, 'b': 2})
    for c in session.cookie_jar:
        print(c.key, c.value)