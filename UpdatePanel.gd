extends Panel

# 更新检测面板
# 用于检测萌芽农场的版本更新

# 配置信息
const GAME_ID = "mengyafarm"  # 游戏ID
const SERVER_URL = "http://192.168.1.112:5000"  # 服务器地址
const CURRENT_VERSION = "2.0.0"  # 当前游戏版本

# UI节点引用
@onready var version_label: Label = $VBoxContainer/VersionLabel
@onready var status_label: Label = $VBoxContainer/StatusLabel
@onready var update_button: Button = $VBoxContainer/UpdateButton
@onready var download_button: Button = $VBoxContainer/DownloadButton
@onready var close_button: Button = $VBoxContainer/CloseButton
@onready var progress_bar: ProgressBar = $VBoxContainer/ProgressBar
@onready var changelog_text: TextEdit = $VBoxContainer/ChangelogText

# HTTP请求节点
var http_request: HTTPRequest

# 更新信息
var update_info = {}
var has_update = false

func _ready():
	# 初始化UI
	setup_ui()
	
	# 创建HTTP请求节点
	http_request = HTTPRequest.new()
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)
	
	# 连接按钮信号
	update_button.pressed.connect(_on_update_button_pressed)
	download_button.pressed.connect(_on_download_button_pressed)
	close_button.pressed.connect(_on_close_button_pressed)
	
	# 自动检查更新
	check_for_updates()

func setup_ui():
	"""初始化UI界面"""
	version_label.text = "当前版本: " + CURRENT_VERSION
	status_label.text = "正在检查更新..."
	update_button.visible = false
	download_button.visible = false
	progress_bar.visible = false
	changelog_text.visible = false
	
	# 设置面板样式
	self.visible = false

func check_for_updates():
	"""检查版本更新"""
	status_label.text = "正在检查更新..."
	progress_bar.visible = true
	progress_bar.value = 0
	
	# 构建检查更新的URL
	var check_url = SERVER_URL + "/api/simple/check-version/" + GAME_ID + "?current_version=" + CURRENT_VERSION
	
	print("检查更新URL: ", check_url)
	
	# 发送HTTP请求
	var error = http_request.request(check_url)
	if error != OK:
		_show_error("网络请求失败: " + str(error))

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
	"""处理HTTP请求响应"""
	progress_bar.visible = false
	
	if response_code != 200:
		_show_error("服务器响应错误: " + str(response_code))
		return
	
	# 解析JSON响应
	var json = JSON.new()
	var parse_result = json.parse(body.get_string_from_utf8())
	
	if parse_result != OK:
		_show_error("解析服务器响应失败")
		return
	
	var response_data = json.data
	
	if "error" in response_data:
		_show_error("服务器错误: " + response_data.error)
		return
	
	# 处理更新检查结果
	if response_data.get("has_update", false):
		_show_update_available(response_data)
	else:
		_show_no_update()

func _show_update_available(data: Dictionary):
	"""显示有更新可用"""
	has_update = true
	update_info = data
	
	status_label.text = "发现新版本: " + data.get("latest_version", "未知")
	status_label.modulate = Color.GREEN
	
	update_button.visible = true
	download_button.visible = true
	
	# 显示更新日志（如果有）
	if "description" in data:
		changelog_text.text = "更新内容:\n" + data.description
		changelog_text.visible = true
	
	# 显示面板
	self.visible = true
	
	print("发现更新: ", data.latest_version)

func _show_no_update():
	"""显示无更新"""
	status_label.text = "已是最新版本"
	status_label.modulate = Color.WHITE
	
	# 可以选择不显示面板，或者显示几秒后自动隐藏
	await get_tree().create_timer(2.0).timeout
	self.visible = false

func _show_error(message: String):
	"""显示错误信息"""
	status_label.text = "错误: " + message
	status_label.modulate = Color.RED
	
	# 显示面板让用户看到错误
	self.visible = true
	
	print("更新检查错误: ", message)

func _on_update_button_pressed():
	"""点击检查更新按钮"""
	check_for_updates()

func _on_download_button_pressed():
	"""点击下载按钮"""
	if not has_update:
		return
	
	var platform = _get_platform_name()
	var download_url = ""
	
	# 优先使用游戏ID下载链接
	download_url = SERVER_URL + "/download/" + GAME_ID + "/" + platform.to_lower()
	
	print("下载链接: ", download_url)
	
	# 尝试打开下载链接
	var error = OS.shell_open(download_url)
	if error != OK:
		# 如果打开失败，尝试复制到剪贴板
		DisplayServer.clipboard_set(download_url)
		_show_message("无法打开浏览器，下载链接已复制到剪贴板")
	else:
		_show_message("正在打开下载页面...")

func _on_close_button_pressed():
	"""关闭更新面板"""
	self.visible = false

func _get_platform_name() -> String:
	"""获取当前平台名称"""
	var os_name = OS.get_name()
	
	match os_name:
		"Windows":
			return "Windows"
		"Android":
			return "Android"
		"macOS":
			return "macOS"
		"Linux":
			return "Linux"
		"iOS":
			return "iOS"
		_:
			return "Windows"  # 默认返回Windows

func _show_message(message: String):
	"""显示临时消息"""
	var original_text = status_label.text
	var original_color = status_label.modulate
	
	status_label.text = message
	status_label.modulate = Color.YELLOW
	
	# 2秒后恢复原文本
	await get_tree().create_timer(2.0).timeout
	status_label.text = original_text
	status_label.modulate = original_color

# 公共方法，供外部调用
func show_update_panel():
	"""显示更新面板"""
	self.visible = true
	check_for_updates()

func hide_update_panel():
	"""隐藏更新面板"""
	self.visible = false

# 可选：自动定期检查更新
func start_auto_check(interval_minutes: int = 30):
	"""开始自动检查更新"""
	var timer = Timer.new()
	add_child(timer)
	timer.wait_time = interval_minutes * 60.0  # 转换为秒
	timer.timeout.connect(check_for_updates)
	timer.start()
	
	print("自动更新检查已启动，间隔: ", interval_minutes, " 分钟") 