# PLEX 手机、平板、网页与 Android 发布

正式前端仍是 `frontend/` 的 Vue 3 工程。浏览器按屏宽使用同一套页面：桌面侧栏、平板窄侧栏、手机底部导航。Android 使用 Capacitor 打包相同的构建产物。

## 运行前提

APK 内只包含前端。登录、试炼、知识服务、上传等功能依赖公网 Flask 后端和数据库。正式发布前须完成：

1. 验证手机可访问的 HTTPS 后端及 `/api/v1/health`。目前使用 `https://106.15.77.40/api`；`pltek.cn` 的 HTTP 请求被云服务商以未备案拦截，域名不能作为正式入口。
2. 准备 Android 发布签名文件（`.jks`）；妥善备份，后续更新必须使用同一密钥。
3. 用真实 HTTPS API 地址构建正式 APK。不要使用 `localhost`、局域网或开发代理地址。构建脚本会检查 `/api/v1/health` 的数据库状态和 Android WebView 的跨域许可。
4. 在 Android 真机上测试登录、学生/教师主流程、上传和退出登录。

## 本地调试包

在 `frontend/` 运行 `npm run android:debug`。APK 位于 `android/app/build/outputs/apk/debug/app-debug.apk`。调试包使用 Android 默认调试签名，且没有公网 API 配置，不适合公开体验。

## 正式签名包

在 `frontend/` 设置环境变量后运行 `npm run android:release`：

```powershell
$env:VITE_API_BASE_URL = 'https://106.15.77.40/api'
$env:PLEX_ANDROID_KEYSTORE = 'C:\secure\plex-release.jks'
$env:PLEX_ANDROID_STORE_PASSWORD = '<签名文件密码>'
$env:PLEX_ANDROID_KEY_ALIAS = 'plex'
$env:PLEX_ANDROID_KEY_PASSWORD = '<密钥密码>'
npm run android:release
```

脚本会检查公网 HTTPS API、数据库、CORS 与签名配置，构建网页、同步 Android 工程，生成 `android/app/build/outputs/apk/release/app-release.apk` 并打印 SHA-256。发布前应更新 `android/app/build.gradle` 的 `versionCode` 和 `versionName`。APK 内暂只提供账号密码登录；第三方 OAuth 仍由网页版提供。

## GitHub Releases

真机验收通过后，可用仓库账号运行：

```powershell
gh release create v1.0.0 frontend/android/app/build/outputs/apk/release/app-release.apk --repo yeniwu46-max/plex --title 'PLEX 1.0.0' --notes 'Android 体验版；需要联网。'
```

公开地址是 `https://github.com/yeniwu46-max/plex/releases/latest`。网页版本目前部署在 `https://106.15.77.40/`，与 APK 使用同一后端。服务器的受信任 IP 证书由 `link-demo-cert-renew.timer` 自动续期；发布后需保持该定时器正常运行。域名完成备案后，应更换为域名证书、更新 API 地址，并递增 Android `versionCode` 后发布新版。

本次发布签名文件和密码只保存在本机用户目录的 `.ssh/plex-android-release.jks` 与 `.ssh/plex-android-release.password`，未提交到仓库。务必安全备份两者，否则后续 APK 无法以同一包名覆盖升级。
