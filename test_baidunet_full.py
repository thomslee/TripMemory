# -*- coding: utf-8 -*-
"""百度网盘API完整测试（用标准库urllib）。"""
import urllib.parse
import urllib.request
import json

APP_KEY = "YOUR_BAIDUNET_APP_KEY"
SECRET_KEY = "YOUR_BAIDUNET_SECRET_KEY"
REDIRECT_URI = "oob"
CODE = "0a5d5940d9d2a27b4fedb6532812aad0"

BASE_URL = "https://pan.baidu.com/rest/2.0"
OPEN_URL = "https://openapi.baidu.com"


def http_get(url, params=None):
    """发送GET请求。"""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def step1_get_token():
    """步骤1：换取access_token。"""
    print("=" * 60)
    print("步骤1：用授权码换取access_token")
    print("=" * 60)
    params = {
        "grant_type": "authorization_code",
        "code": CODE,
        "client_id": APP_KEY,
        "client_secret": SECRET_KEY,
        "redirect_uri": REDIRECT_URI,
    }
    result = http_get(f"{OPEN_URL}/oauth/2.0/token", params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result.get("access_token")


def step2_user_info(access_token):
    """步骤2：获取用户信息。"""
    print("\n" + "=" * 60)
    print("步骤2：获取用户信息")
    print("=" * 60)
    params = {
        "method": "uinfo",
        "access_token": access_token,
    }
    result = http_get(f"{BASE_URL}/xpan/nas", params)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def step3_list_files(access_token, dir="/"):
    """步骤3：获取文件列表。"""
    print("\n" + "=" * 60)
    print(f"步骤3：获取文件列表 (目录: {dir})")
    print("=" * 60)
    params = {
        "method": "list",
        "access_token": access_token,
        "dir": dir,
        "web": "web",
    }
    result = http_get(f"{BASE_URL}/xpan/file", params)
    if "list" in result:
        print(f"文件数量: {len(result['list'])}")
        for f in result["list"][:15]:
            ftype = "文件夹" if f.get("isdir") == 1 else "文件"
            print(f"  [{ftype}] {f.get('server_filename')} (fs_id={f.get('fs_id')}, size={f.get('size')})")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result.get("list", [])


def step4_file_metadata(access_token, fs_ids):
    """步骤4：获取文件元数据（检查EXIF）。"""
    print("\n" + "=" * 60)
    print(f"步骤4：获取文件元数据 (fs_ids={fs_ids})")
    print("=" * 60)
    fs_ids_str = ",".join(str(fid) for fid in fs_ids)
    params = {
        "method": "filemetas",
        "access_token": access_token,
        "fsids": f"[{fs_ids_str}]",
        "dlink": 1,
        "extra": 1,
    }
    result = http_get(f"{BASE_URL}/xpan/multimedia", params)
    if "list" in result:
        for item in result["list"]:
            print(f"文件名: {item.get('server_filename')}")
            print(f"  大小: {item.get('size')}")
            print(f"  下载链接: {item.get('dlink', 'N/A')}")
            print(f"  路径: {item.get('path')}")
            if "extra" in item:
                print(f"  extra: {json.dumps(item['extra'], ensure_ascii=False)}")
            print(f"  所有字段: {list(item.keys())}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def step5_search_photos(access_token):
    """步骤5：搜索图片文件。"""
    print("\n" + "=" * 60)
    print("步骤5：搜索图片文件")
    print("=" * 60)
    params = {
        "method": "search",
        "access_token": access_token,
        "key": ".jpg",
        "web": "web",
        "num": 10,
        "page": 1,
    }
    result = http_get(f"{BASE_URL}/xpan/file", params)
    if "list" in result:
        print(f"找到 {len(result['list'])} 个jpg文件")
        for f in result["list"][:5]:
            print(f"  - {f.get('server_filename')} (fs_id={f.get('fs_id')}, path={f.get('path')})")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result.get("list", [])


if __name__ == "__main__":
    access_token = step1_get_token()
    if not access_token:
        print("\n获取token失败，退出！")
        exit(1)

    step2_user_info(access_token)
    files = step3_list_files(access_token, "/")

    file_items = [f for f in files if f.get("isdir") == 0]
    if file_items:
        step4_file_metadata(access_token, [file_items[0]["fs_id"]])

    photos = step5_search_photos(access_token)
    if photos:
        step4_file_metadata(access_token, [photos[0]["fs_id"]])

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
