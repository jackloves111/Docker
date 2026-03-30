import os
import hashlib

LICENSE_SALT = "NaS_Tools_2024_Salt_KEY"
UUID_PATH = "/host_uuid"
LICENSE_PATH = "/config/license.dat"


def get_host_uuid():
    try:
        with open(UUID_PATH, "r") as f:
            uuid = f.read().strip()
            return uuid.lower() if uuid else None
    except (FileNotFoundError, PermissionError, IOError):
        return None


def generate_signature(uuid):
    signature = hashlib.sha256(f"{uuid}{LICENSE_SALT}".encode()).hexdigest()
    return signature


def verify_license():
    uuid = get_host_uuid()
    if not uuid:
        return False, "无法读取主机 UUID"

    if not os.path.exists(LICENSE_PATH):
        return False, "License 文件不存在"

    try:
        with open(LICENSE_PATH, "r") as f:
            stored_signature = f.read().strip()

        calculated = generate_signature(uuid)

        if calculated == stored_signature:
            return True, "License 验证通过"
        else:
            return False, "License 验证失败"
    except (FileNotFoundError, PermissionError, IOError) as e:
        return False, f"License 文件读取失败: {e}"


def is_license_valid():
    valid, _ = verify_license()
    return valid