// 终端命令配置文件
// 你可以在这里轻松地添加、删除或修改要显示的命令

const TERMINAL_COMMANDS = [
    {
        type: 'command',
        user: 'root@ubuntu',
        path: '~',
        prompt: '#',
        command: 'apt update && apt upgrade',
        params: '-y'
    },
    {
        type: 'output',
        text: 'Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease',
        color: 'output'
    },
    {
        type: 'command',
        user: 'developer@debian',
        path: '/home/dev/projects',
        prompt: '$',
        command: 'git clone',
        params: 'https://github.com/torvalds/linux.git'
    },
    {
        type: 'output',
        text: 'Cloning into \'linux\'... remote: Enumerating objects: 8234567, done.',
        color: 'success'
    },
    {
        type: 'command',
        user: 'admin@centos',
        path: '/opt/docker',
        prompt: '$',
        command: 'docker-compose up',
        params: '-d --build'
    },
    {
        type: 'output',
        text: 'Creating network "app_default" with the default driver',
        color: 'info'
    },
    {
        type: 'command',
        user: 'user@arch',
        path: '~/workspace',
        prompt: '$',
        command: 'pacman -Syu',
        params: '--noconfirm'
    },
    {
        type: 'output',
        text: '::Synchronizing package databases... core 132.8 KiB  1234 KiB/s',
        color: 'output'
    },
    {
        type: 'command',
        user: 'root@fedora',
        path: '/var/log',
        prompt: '#',
        command: 'tail -f',
        params: 'httpd/access_log'
    },
    {
        type: 'output',
        text: '192.168.1.100 - - [15/Jan/2024:14:30:25 +0000] "GET /api/v1/status HTTP/1.1" 200 512',
        color: 'output'
    },
    {
        type: 'command',
        user: 'jenkins@ci',
        path: '/var/jenkins_home/workspace',
        prompt: '$',
        command: 'mvn clean package',
        params: '-DskipTests'
    },
    {
        type: 'output',
        text: '[INFO] Building jar: /workspace/target/app-1.0.0-SNAPSHOT.jar',
        color: 'info'
    },
    {
        type: 'command',
        user: 'sysadmin@opensuse',
        path: '/etc/nginx',
        prompt: '$',
        command: 'nginx -t',
        params: '&& systemctl reload nginx',
        comment: true
    },
    {
        type: 'output',
        text: 'nginx: configuration file /etc/nginx/nginx.conf test is successful',
        color: 'success'
    },
    {
        type: 'command',
        user: 'bigmengya@alpine',
        path: '/app',
        prompt: '$',
        command: 'kubectl get pods',
        params: '-n production'
    },
    {
        type: 'output',
        text: 'NAME                    READY   STATUS    RESTARTS   AGE',
        color: 'info'
    },
    {
        type: 'command',
        user: 'root@kali',
        path: '/root',
        prompt: '#',
        command: 'nmap -sS -O',
        params: 'target.example.com'
    },
    {
        type: 'output',
        text: 'Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 14:30 UTC',
        color: 'warning'
    },
    {
        type: 'command',
        user: 'developer@mint',
        path: '~/myproject',
        prompt: '$',
        command: 'npm run build',
        params: '--production'
    }
];

// 颜色映射
const COLOR_CLASSES = {
    'prompt': 'cmd-prompt',
    'user': 'cmd-user', 
    'path': 'cmd-path',
    'command': 'cmd-command',
    'param': 'cmd-param',
    'output': 'cmd-output',
    'error': 'cmd-error',
    'success': 'cmd-success',
    'info': 'cmd-info',
    'warning': 'cmd-warning',
    'comment': 'cmd-comment'
};

// 生成终端行HTML的函数
function generateTerminalLine(config) {
    if (config.type === 'command') {
        let html = `<span class="${COLOR_CLASSES.user}">${config.user}:</span>`;
        html += `<span class="${COLOR_CLASSES.path}">${config.path}</span>`;
        html += `<span class="${COLOR_CLASSES.prompt}">${config.prompt} </span>`;
        html += `<span class="${COLOR_CLASSES.command}">${config.command}</span>`;
        
        if (config.params) {
            if (config.comment) {
                html += ` <span class="${COLOR_CLASSES.comment}">${config.params}</span>`;
            } else {
                html += ` <span class="${COLOR_CLASSES.param}">${config.params}</span>`;
            }
        }
        
        return html;
    } else if (config.type === 'output') {
        return `<span class="${COLOR_CLASSES[config.color] || COLOR_CLASSES.output}">${config.text}</span>`;
    }
    
    return '';
}

// 初始化终端背景
function initTerminalBackground() {
    const container = document.querySelector('.terminal-container');
    if (!container) return;
    
    // 清空现有内容
    container.innerHTML = '';
    
    // 生成所有终端行
    TERMINAL_COMMANDS.forEach((config, index) => {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = generateTerminalLine(config);
        container.appendChild(line);
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initTerminalBackground); 