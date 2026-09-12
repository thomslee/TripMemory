# -*- coding: utf-8 -*-
"""百度网盘API测试脚本。"""
import httpx
import urllib.parse

# 从图片中读取的密钥（占位，实际值请在本地 .env 配置）
APP_KEY = "YOUR_BAIDUNET_APP_KEY"
SECRET_KEY = "YOUR_BAIDUNET_SECRET_KEY"
REDIRECT_URI = "oob"  # 桌面应用使用oob，授权后显示code

BASE_URL = "https://pan.baidu.com/rest/2.0"
OPEN_URL = "https://openapi.baidu.com"


def get_auth_url():
    """生成授权URL。"""
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": REDIRECT_URI,
        "scope": "basic,netdisk",
        "display": "page",
    }
    url = f"{OPEN_URL}/oauth/2.0/authorize?{urllib.parse.urlencode(params)}"
    return url


def get_access_token(code: str):
    """用授权码换取access_token。"""
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": APP_KEY,
        "client_secret": SECRET_KEY,
        "redirect_uri": REDIRECT_URI,
    }
    resp = httpx.get(f"{OPEN_URL}/oauth/2.0/token", params=params, timeout=30)
    return resp.json()


def list_files(access_token: str, dir: str = "/"):
    """获取文件列表。"""
    params = {
        "method": "list",
        "access_token": access_token,
        "dir": dir,
        "web": "web",
    }
    resp = httpx.get(f"{BASE_URL}/xpan/file", params=params, timeout=30)
    return resp.json()


def get_file_metadata(access_token: str, fs_ids: list[int]):
    """获取文件元数据（含EXIF）。"""
    fs_ids_str = ",".join(str(fid) for fid in fs_ids)
    params = {
        "method": "filemetas",
        "access_token": access_token,
        "fsids": f"[{fs_ids_str}]",
        "dlink": 1,
        "extra": 1,
    }
    resp = httpx.get(f"{BASE_URL}/xpan/multimedia", params=params, timeout=30)
    return resp.json()


def get_user_info(access_token: str):
    """获取用户信息。"""
    params = {
        "method": "uinfo",
        "access_token": access_token,
    }
    resp = httpx.get(f"{BASE_URL}/xpan/nas", params=params, timeout=30)
    return resp.json()


if __name__ == "__main__":
    print("=" * 60)
    print("百度网盘API测试")
    print("=" * 60)
    print()

    # 步骤1：生成授权URL
    auth_url = get_auth_url()
    print("步骤1：请在浏览器中打开以下URL进行授权：")
    print(auth_url)
    print()
    print("授权后会显示一个授权码（code），请复制下来。")
    print()

    code = input("请输入授权码(code): ").strip()
    if not code:
        print("未输入授权码，退出。")
        exit(1)

    # 步骤2：换取access_token
    print("\n步骤2：用授权码换取access_token...")
    token_result = get_access_token(code)
    print(f"结果: {token_result}")

    if "access_token" not in token_result:
        print("获取token失败！")
        exit(1)

    access_token = token_result["access_token"]
    print(f"\naccess_token: {access_token[:20]}...")
    print(f"有效期: {token_result.get('expires_in')}秒")

    # 步骤3：获取用户信息
    print("\n步骤3：获取用户信息...")
    user_info = get_user_info(access_token)
    print(f"结果: {user_info}")

    # 步骤4：获取根目录文件列表
    print("\n步骤4：获取根目录文件列表...")
    files = list_files(access_token, "/")
    if "list" in files:
        print(f"文件数量: {len(files['list'])}")
        for f in files["list"][:10]:
            print(f"  - {f.get('server_filename')} (fs_id={f.get('fs_id')}, size={f.get('size')}, isdir={f.get('isdir')})")
    else:
        print(f"结果: {files}")

    # 步骤5：测试获取文件元数据（如果有文件）
    if "list" in files and files["list"]:
        # 找一个文件（非目录）
        file_item = None
        for f in files["list"]:
            if f.get("isdir") == 0:
                file_item = f
                break
        if file_item:
            print(f"\n步骤5：获取文件元数据（{file_item.get('server_filename')}）...")
            meta = get_file_metadata(access_token, [file_item["fs_id"]])
            print(f"结果: {meta}")
            if "list" in meta and meta["list"]:
                item = meta["list"][0]
                print(f"  文件名: {item.get('server_filename')}")
                print(f"  大小: {item.get('size')}")
                print(f"  下载链接: {item.get('dlink', 'N/A')}")
                # 检查是否有EXIF信息
                if "extra" in item:
                    print(f"  extra信息: {item['extra']}")
        else:
            print("\n步骤5：根目录没有文件，跳过元数据测试。")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
