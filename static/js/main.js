// 値下げスカウター メインJavaScript

// DOMの読み込み完了時に実行
document.addEventListener('DOMContentLoaded', function() {
    console.log('値下げスカウター JS loaded');
    
    // ナビゲーションのアクティブクラス自動設定（必要に応じて）
    setActiveNavItem();
    
    // Bootstrapツールチップの初期化
    initTooltips();
});

// 現在のURLパスに基づいてナビゲーションのアクティブ項目を設定
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        // リンクのhref属性から相対パスを取得
        const linkPath = new URL(link.href).pathname;
        
        // 完全一致または、サブディレクトリの場合はスタートワイズ一致
        if (currentPath === linkPath || 
            (linkPath !== '/' && currentPath.startsWith(linkPath))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Bootstrapツールチップの初期化
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}