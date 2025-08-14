[app]
title = PDF Fill & Sign
package.name = pdfsignfinal
package.domain = org.example
source.dir = app
source.include_exts = py,png,jpg,kv,atlas,yaml,pdf,txt
version = 1.0
requirements = python3,kivy,pyyaml,reportlab,pypdf2,pillow
orientation = landscape
fullscreen = 0
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
[app]
# ...existing lines...
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
