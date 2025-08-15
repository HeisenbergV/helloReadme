/**
 * helloReadme 主要JavaScript文件
 */

// 全局变量
let currentPage = 1;
let isLoading = false;

// 页面加载完成后执行
$(document).ready(function() {
    // 初始化工具提示
    initTooltips();
    
    // 初始化事件监听器
    initEventListeners();
    
    // 初始化页面特定功能
    initPageSpecific();
});

/**
 * 初始化Bootstrap工具提示
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 初始化事件监听器
 */
function initEventListeners() {
    // 自动隐藏警告框
    $('.alert').on('closed.bs.alert', function() {
        // 警告框关闭后的处理
    });
    
    // 表单验证
    $('form').on('submit', function(e) {
        if (!validateForm(this)) {
            e.preventDefault();
            return false;
        }
    });
    
    // 搜索框实时搜索
    $('#search-input').on('input', debounce(function() {
        performSearch($(this).val());
    }, 300));
}

/**
 * 初始化页面特定功能
 */
function initPageSpecific() {
    const currentPath = window.location.pathname;
    
    if (currentPath === '/') {
        // 首页特定功能
        initHomePage();
    } else if (currentPath === '/projects') {
        // 项目列表页特定功能
        initProjectsPage();
    } else if (currentPath === '/collect') {
        // 采集页特定功能
        initCollectPage();
    } else if (currentPath === '/stats') {
        // 统计页特定功能
        initStatsPage();
    }
}

/**
 * 初始化首页功能
 */
function initHomePage() {
    // 可以添加首页特定的功能
    console.log('首页功能初始化完成');
}

/**
 * 初始化项目列表页功能
 */
function initProjectsPage() {
    // 筛选器变化时自动提交
    $('#language, #min_stars, #per_page').on('change', function() {
        $('#filter-form').submit();
    });
    
    // 项目卡片悬停效果
    $('.project-card').hover(
        function() {
            $(this).addClass('shadow-lg');
        },
        function() {
            $(this).removeClass('shadow-lg');
        }
    );
}

/**
 * 初始化采集页功能
 */
function initCollectPage() {
    // 采集方式变化处理
    $('#collection_type').on('change', function() {
        updateCollectionForm($(this).val());
    });
    
    // 实时验证
    $('#query').on('input', function() {
        validateQuery($(this).val());
    });
}

/**
 * 初始化统计页功能
 */
function initStatsPage() {
    // 可以添加统计页特定的功能
    console.log('统计页功能初始化完成');
}

/**
 * 表单验证
 */
function validateForm(form) {
    let isValid = true;
    const requiredFields = $(form).find('[required]');
    
    requiredFields.each(function() {
        if (!$(this).val().trim()) {
            showFieldError($(this), '此字段为必填项');
            isValid = false;
        } else {
            clearFieldError($(this));
        }
    });
    
    return isValid;
}

/**
 * 显示字段错误
 */
function showFieldError(field, message) {
    const errorDiv = field.siblings('.invalid-feedback');
    if (errorDiv.length === 0) {
        field.after(`<div class="invalid-feedback">${message}</div>`);
    } else {
        errorDiv.text(message);
    }
    field.addClass('is-invalid');
}

/**
 * 清除字段错误
 */
function clearFieldError(field) {
    field.removeClass('is-invalid');
    field.siblings('.invalid-feedback').remove();
}

/**
 * 查询验证
 */
function validateQuery(query) {
    const queryField = $('#query');
    
    if (query.length < 2) {
        showFieldError(queryField, '查询内容至少需要2个字符');
        return false;
    } else {
        clearFieldError(queryField);
        return true;
    }
}

/**
 * 更新采集表单
 */
function updateCollectionForm(collectionType) {
    const queryGroup = $('#query-group');
    const languageGroup = $('#language-group');
    const queryHelp = $('#query-help');
    
    switch(collectionType) {
        case 'search':
            queryGroup.find('label').text('搜索关键词');
            queryHelp.text('搜索关键词，如：AI machine learning');
            languageGroup.show();
            break;
        case 'user':
            queryGroup.find('label').text('GitHub用户名');
            queryHelp.text('输入GitHub用户名，如：microsoft');
            languageGroup.hide();
            break;
        case 'org':
            queryGroup.find('label').text('组织名称');
            queryHelp.text('输入GitHub组织名，如：openai');
            languageGroup.hide();
            break;
    }
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 执行搜索
 */
function performSearch(query) {
    if (query.length < 2) {
        return;
    }
    
    // 这里可以实现实时搜索功能
    console.log('执行搜索:', query);
}

/**
 * 显示加载状态
 */
function showLoading(element, text = '加载中...') {
    element.prop('disabled', true);
    element.html(`<span class="spinner-border spinner-border-sm me-2" role="status"></span>${text}`);
}

/**
 * 隐藏加载状态
 */
function hideLoading(element, originalText) {
    element.prop('disabled', false);
    element.html(originalText);
}

/**
 * 显示成功消息
 */
function showSuccessMessage(message, duration = 5000) {
    const alert = $(`
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('.container').first().prepend(alert);
    
    // 自动隐藏
    setTimeout(() => {
        alert.alert('close');
    }, duration);
    
    // 滚动到顶部
    $('html, body').animate({ scrollTop: 0 }, 500);
}

/**
 * 显示错误消息
 */
function showErrorMessage(message, duration = 5000) {
    const alert = $(`
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('.container').first().prepend(alert);
    
    // 自动隐藏
    setTimeout(() => {
        alert.alert('close');
    }, duration);
    
    // 滚动到顶部
    $('html, body').animate({ scrollTop: 0 }, 500);
}

/**
 * 格式化数字
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) {
        return '昨天';
    } else if (diffDays < 7) {
        return `${diffDays}天前`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks}周前`;
    } else if (diffDays < 365) {
        const months = Math.floor(diffDays / 30);
        return `${months}个月前`;
    } else {
        return date.toLocaleDateString('zh-CN');
    }
}

/**
 * 复制到剪贴板
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showSuccessMessage('已复制到剪贴板');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

/**
 * 备用复制方法
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccessMessage('已复制到剪贴板');
    } catch (err) {
        showErrorMessage('复制失败');
    }
    
    document.body.removeChild(textArea);
}

/**
 * 导出数据
 */
function exportData(format = 'json') {
    // 这里可以实现数据导出功能
    console.log('导出数据:', format);
}

/**
 * 页面加载完成后的通用处理
 */
$(window).on('load', function() {
    // 隐藏加载动画
    $('.loading-overlay').fadeOut();
    
    // 初始化懒加载
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
});
