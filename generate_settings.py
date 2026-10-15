"""Offline experimental settings.dat generator for NetEase Music UWP 1.4.1.0.

Only Python's standard library and Windows are required. No private template,
network requests or credential discovery are used.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import re
import shutil
import struct
import tempfile
import time
import winreg
from ctypes import wintypes as W
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRING, INT32, INT64, BOOL = 0x05F5E10C, 0x05F5E104, 0x05F5E106, 0x05F5E10B


def make_cookies(musicu: str, csrf: str = '', nmtid: str = '') -> str:
    supplied = musicu.strip()
    cookies = {}
    if '=' in supplied:
        for part in supplied.split(';'):
            if '=' not in part:
                continue
            name, value = part.strip().split('=', 1)
            if name:
                cookies[name] = value.strip()
        token = cookies.get('MUSIC_U', '')
    else:
        token = supplied
        cookies['MUSIC_U'] = token
    if not re.fullmatch(r'[0-9a-fA-F]+', token):
        raise ValueError('MUSIC_U 必须是十六进制值，或包含 MUSIC_U 的完整 Cookie。')
    for name, value in (('__csrf', csrf.strip()), ('NMTID', nmtid.strip())):
        if value:
            if any(c in value for c in ';\r\n\x00'):
                raise ValueError(name + ' 包含非法分隔符。')
            cookies[name] = value
    if any(any(c in v for c in '\r\n\x00') for v in cookies.values()):
        raise ValueError('Cookie 不可包含换行或空字符。')
    cookies.setdefault('__remember_me', 'true')
    return '; '.join(name + '=' + value for name, value in cookies.items())


def encode_value(kind: int, value, timestamp: bytes) -> bytes:
    if kind == STRING:
        payload = (str(value) + '\x00').encode('utf-16-le')
    elif kind == INT32:
        payload = struct.pack('<i', value)
    elif kind == INT64:
        payload = struct.pack('<q', value)
    elif kind == BOOL:
        payload = bytes([bool(value)])
    else:
        raise ValueError('Unsupported UWP type')
    return payload + timestamp


def fields_for_account(userid: int, cookies: str, nickname: str, account_type: int, playlist_id: int):
    """Known structural fields with user inputs or neutral defaults only."""
    users = {
        'cookies': (STRING, cookies),
        'likePlaylistId': (INT64, playlist_id),
        'subRadioCount': (INT32, 0), 'subArtistCount': (INT32, 0),
        'unreadNoticeMsgCount': (INT32, 0), 'unreadPrivateMsgCount': (INT32, 0),
        'level': (INT32, 0), 'VipUser': (BOOL, False),
        'VipExpireTime': (INT64, 0), 'VipOldVersion': (BOOL, False),
    }
    profile = {
        'userid': (INT64, userid), 'nickname': (STRING, nickname),
        'avatarImgId': (INT64, 0), 'birthday': (INT64, 0),
        'blacklist': (BOOL, False),
    }
    for name in ('avatarUrl', 'backgroundUrl', 'description', 'detailDescription', 'signature'):
        profile[name] = (STRING, '')
    profile['experttags'] = (STRING, '[]')
    for name in ('city', 'province', 'eventCount', 'followeds', 'gender', 'playlistBeSubscribedCount', 'vipType', 'cCount', 'sCount'):
        profile[name] = (INT32, 0)
    fields = {
        'LocalState\\usersettings': users,
        'LocalState\\usersettings\\account': {
            'id': (INT64, userid), 'type': (INT32, account_type), 'anonimousUser': (BOOL, False),
        },
        'LocalState\\usersettings\\profile': profile,
    }
    # The real logged-in sample has sentinel -1 IDs in these bindings; do not
    # substitute the user's ID into unrelated third-party identity fields.
    for binding in ('doubanBinding', 'microsoftBinding', 'neteaseBinding', 'phoneBinding', 'QQBinding', 'sinaWeiboBinding', 'weixinBinding'):
        fields['LocalState\\usersettings\\' + binding] = {
            'id': (INT64, -1), 'url': (STRING, ''), 'tokenJsonStr': (STRING, ''),
            'expired': (BOOL, False), 'expiresIn': (INT32, 0), 'refreshTime': (INT32, 0),
        }
    return fields


def generate(output: Path, musicu: str, userid: str, nickname: str = '', csrf: str = '', nmtid: str = '', account_type: int = 1, playlist_id: int = -1) -> Path:
    try:
        uid = int(userid)
    except (ValueError, TypeError):
        raise ValueError('用户 ID 必须是正整数。') from None
    if not 0 < uid < 2**63:
        raise ValueError('用户 ID 必须是正的 64 位整数。')
    if account_type < 0 or account_type >= 2**31:
        raise ValueError('账号类型超出范围。')
    if not -1 <= playlist_id < 2**63:
        raise ValueError('喜欢歌单 ID 必须为 -1 或非负整数。')
    if '\x00' in nickname:
        raise ValueError('昵称不能包含空字符。')
    cookie = make_cookies(musicu, csrf, nmtid)
    seed = HERE / 'blank.dat'
    output = Path(output).resolve()
    if output == seed.resolve():
        raise ValueError('不能覆盖程序附带的空白 Hive。')
    output.parent.mkdir(parents=True, exist_ok=True)
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    load = api.RegLoadAppKeyW
    load.argtypes = [W.LPCWSTR, ctypes.POINTER(W.HANDLE), W.DWORD, W.DWORD, W.DWORD]
    load.restype = W.LONG
    write = api.RegSetValueExW
    write.argtypes = [W.HANDLE, W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD]
    write.restype = W.LONG
    stamp = struct.pack('<Q', time.time_ns() // 100 + 116444736000000000)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        working = Path(temp) / 'settings.dat'
        shutil.copyfile(seed, working)
        handle = W.HANDLE()
        status = load(str(working), ctypes.byref(handle), winreg.KEY_ALL_ACCESS, 0, 0)
        if status:
            raise ctypes.WinError(status)
        try:
            winreg.SetValueEx(handle.value, 'Version', 0, winreg.REG_DWORD, 1220)
            for path, fields in fields_for_account(uid, cookie, nickname, account_type, playlist_id).items():
                with winreg.CreateKeyEx(handle.value, path, 0, winreg.KEY_ALL_ACCESS) as key:
                    for name, (kind, value) in fields.items():
                        data = encode_value(kind, value, stamp)
                        buffer = ctypes.create_string_buffer(data)
                        status = write(int(key), name, 0, kind, buffer, len(data))
                        if status:
                            raise ctypes.WinError(status)
            winreg.FlushKey(handle.value)
        finally:
            winreg.CloseKey(handle.value)
        os.replace(working, output)
    return output


def main():
    parser = argparse.ArgumentParser(description='网易云 UWP 1.4.1.0 登录文件生成器')
    parser.add_argument('--musicu', required=True, help='MUSIC_U 值或完整 Cookie')
    parser.add_argument('--userid', required=True, help='用户 ID，不是手机号')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        path = generate(args.out, args.musicu, args.userid)
        print('已生成：' + str(path))
        return 0
    except (ValueError, OSError) as exc:
        print('生成失败：' + str(exc))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
