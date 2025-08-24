// 编程词汇漂浮效果配置
// 你可以在这里添加、删除或修改要显示的编程词汇

const PROGRAMMING_WORDS = {
    // 英文编程关键词
    english: [
        "Python","Java","C++","C","JavaScript","HTML","CSS","SQL","Linux","Shell","Git","Docker","Kubernetes","Jenkins","CI/CD",
        "Node.js","PostgreSQL","SQLite","SQLServer","Redis","MySQL","MongoDB","PostgreSQL","SQLite",
        "PHP","Unity","Godot","Unreal","Blender","Photoshop","Maya","3DS Max","Blender",
    ]
};

// 词汇类型配置
const WORD_TYPES = [
    { type: 'english', className: 'english', weight: 1.0}
];

// 生成随机词汇
function getRandomWord() {
    // 根据权重随机选择词汇类型
    const random = Math.random();
    let cumulativeWeight = 0;
    
    for (const wordType of WORD_TYPES) {
        cumulativeWeight += wordType.weight;
        if (random <= cumulativeWeight) {
            const words = PROGRAMMING_WORDS[wordType.type];
            const randomIndex = Math.floor(Math.random() * words.length);
            return {
                text: words[randomIndex],
                className: wordType.className
            };
        }
    }
    
    // 默认返回英文词汇
    const words = PROGRAMMING_WORDS.english;
    const randomIndex = Math.floor(Math.random() * words.length);
    return {
        text: words[randomIndex],
        className: 'english'
    };
}

// 创建漂浮词汇元素
function createFloatingWord() {
    const container = document.querySelector('.floating-words');
    if (!container) return;
    
    const word = getRandomWord();
    const element = document.createElement('div');
    
    element.className = `floating-word ${word.className}`;
    element.textContent = word.text;
    
    // 随机水平位置（在右侧区域内）
    const leftPosition = Math.random() * 250; // 0-250px 范围内
    element.style.left = leftPosition + 'px';
    
    // 随机动画延迟和持续时间
    const delay = Math.random() * 5; // 0-5秒延迟
    const duration = 15 + Math.random() * 10; // 15-25秒持续时间
    
    element.style.animationDelay = delay + 's';
    element.style.animationDuration = duration + 's';
    
    container.appendChild(element);
    
    // 动画结束后移除元素
    setTimeout(() => {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }, (delay + duration) * 1000);
}

// 检查设置并初始化漂浮词汇效果
async function checkSettingsAndInit() {
    try {
        const response = await fetch('/static/data/settings.json');
        const settings = await response.json();
        
        // 如果设置中关闭了漂浮词特效，则隐藏容器
        if (settings['一键关闭漂浮词特效'] === true) {
            console.log('漂浮词特效已被设置关闭');
            const container = document.querySelector('.floating-words');
            if (container) {
                container.style.display = 'none';
            }
            return;
        }
        
        // 启动漂浮词效果
        initFloatingWords();
    } catch (error) {
        console.error('读取设置失败，使用默认配置:', error);
        // 如果读取设置失败，默认启动特效
        initFloatingWords();
    }
}

// 初始化漂浮词汇效果
function initFloatingWords() {
    // 立即创建一些词汇
    for (let i = 0; i < 15; i++) {
        setTimeout(() => createFloatingWord(), i * 2000);
    }
    
    // 定期创建新的词汇
    setInterval(() => {
        createFloatingWord();
    }, 1000); // 每3秒创建一个新词汇
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 延迟1秒开始，避免与页面加载冲突
    setTimeout(checkSettingsAndInit, 1000);
});