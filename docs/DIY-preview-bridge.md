---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_b90adc81957d11f181ac525400f8a581
    ReservedCode1: vAbMv8zdU2mnaXZucWtBpIATcZC6t7V6nWTZKznt+P++qS9ejI5yXuPS+qB3Nh2yT2idukY4VkeIRf5erheKeeb+gh8tOxnR5gWlU3HY1jpE11ztRDzMbZOYeJjrQ/WMEnn8j2/8BkvtuZoeYzoXenS3pl45QrHFwAnEd+BS9bpcT81paPEjm2HCmQE=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_b90adc81957d11f181ac525400f8a581
    ReservedCode2: vAbMv8zdU2mnaXZucWtBpIATcZC6t7V6nWTZKznt+P++qS9ejI5yXuPS+qB3Nh2yT2idukY4VkeIRf5erheKeeb+gh8tOxnR5gWlU3HY1jpE11ztRDzMbZOYeJjrQ/WMEnn8j2/8BkvtuZoeYzoXenS3pl45QrHFwAnEd+BS9bpcT81paPEjm2HCmQE=
---

# DIY 装修编辑器 - iframe 预览双向交互桥接

> 状态：设计文档（待实现）
> 关联分支：`feature/diy-preview-bridge`
> 前置依赖：`portal-web/app/plugins/diy-preview.client.ts` 已存在（保持 SPA 导航的 preview=true 查询参数）

---

## 1. 目标

在 Admin (A) 的页面装修编辑器中，通过 iframe 嵌入 Nuxt C 端 (B) 页面进行实时预览，实现以下闭环：

- A 开启元素选择模式 → B 中 hover/click 元素高亮选中
- 选中元素的 CSS 属性提取到 A 的属性面板
- A 属性面板修改参数 → B 中对应元素即时更新样式
- A 站点配置修改 → B 中品牌/主题色/导航等即时反映

---

## 2. 整体架构

```
┌──────────────────────────────────────┐                 ┌───────────────────────────┐
│  Admin (A) - Vite Vue3               │   postMessage   │  portal-web (B) - Nuxt 3  │
│                                      │ ◄──────────────►│                           │
│  diy/index.vue                       │                 │  plugins/                 │
│  ├─ iframe (src=/portal-preview/zh)  │  start-select    │  diy-preview.client.ts    │
│  ├─ 消息监听 + 发送                  │  stop-select     │  (已有: 补 preview=true)  │
│  └─ 模式切换 / iframeKey 联动       │  apply-styles    │                           │
│                                      │  apply-config    │  preview-bridge.client.ts │
│  store/modules/diy/index.ts          │  revert-styles   │  (新建: 桥接核心)         │
│  ├─ selectedElement (reactive)       │                  │  ├─ 检测 ?preview=true    │
│  ├─ appliedElementStyles (Map)       │  element-selected│  ├─ 元素选择模式          │
│  └─ elementSelectMode                │  element-deselect│  ├─ 样式覆盖/还原         │
│                                      │  bridge-ready    │  └─ 站点配置注入          │
│  diy-editor/modules/                 │                  │                           │
│  PropertyPanel.vue                   │                  │                           │
│  └─ 新增「选中元素」区块             │                  │                           │
└──────────────────────────────────────┘                 └───────────────────────────┘
```

---

## 3. postMessage 协议

### 3.1 消息格式

所有消息为 JSON 序列化：

```ts
interface BridgeMessage {
  type: string;       // 消息类型，如 'marvis:start-select'
  payload?: unknown;  // 携带数据
}
```

### 3.2 A → B 消息（Admin 发给 Nuxt）

| 消息类型 | payload | 说明 |
|----------|---------|------|
| `marvis:start-select` | 无 | 开启元素选择模式，B 给 body 加 `.marvis-selecting` 类 |
| `marvis:stop-select` | 无 | 关闭元素选择模式，清除所有高亮和选中 |
| `marvis:apply-styles` | `{ selector: string, styles: Record<string, string> }` | 对 selector 匹配的元素设置内联 style |
| `marvis:revert-styles` | `{ selector: string }` | 移除 selector 匹配元素上的所有内联 style（还原） |
| `marvis:apply-config` | `{ brand, theme, nav, footer, … }` | 将站点配置实时注入 DOM（CSS 变量 + DOM 修改） |

### 3.3 B → A 消息（Nuxt 发给 Admin）

| 消息类型 | payload | 说明 |
|----------|---------|------|
| `marvis:bridge-ready` | 无 | B 桥接插件初始化完毕 |
| `marvis:element-selected` | 见 3.4 | 用户在 B 中点击选中了某个元素 |
| `marvis:element-deselected` | 无 | 用户点击空白区域取消选中 |

### 3.4 element-selected payload 结构

```ts
{
  selector: string;           // 唯一 CSS 选择器，如 'header.hero > h1:nth-child(1)'
  tag: string;                // 标签名，如 'DIV'
  id: string;                 // id 属性值（可为空）
  classes: string[];          // class 列表
  textContent: string;        // 文本内容（截断到 100 字符）
  rect: {                     // 元素在 iframe 视口中的位置
    top: number;
    left: number;
    width: number;
    height: number;
  };
  computedStyles: {           // 用户关心的关键 CSS 属性
    color: string;
    backgroundColor: string;
    fontSize: string;
    fontWeight: string;
    fontFamily: string;
    textAlign: string;
    lineHeight: string;
    letterSpacing: string;
    padding: string;          // 简写，如 '80px 40px'
    paddingTop: string;
    paddingRight: string;
    paddingBottom: string;
    paddingLeft: string;
    margin: string;
    marginTop: string;
    marginRight: string;
    marginBottom: string;
    marginLeft: string;
    border: string;
    borderRadius: string;
    borderWidth: string;
    borderColor: string;
    borderStyle: string;
    width: string;
    height: string;
    maxWidth: string;
    opacity: string;
    display: string;
    flexDirection: string;
    justifyContent: string;
    alignItems: string;
    gap: string;
    boxShadow: string;
    cursor: string;
  };
}
```

---

## 4. B 侧实现：preview-bridge.client.ts

### 4.1 文件位置

`portal-web/app/plugins/preview-bridge.client.ts`

> 注意：Nuxt 插件在 `app/plugins/` 目录中，文件名以 `.client.ts` 结尾表示仅客户端运行。
> 已有 `diy-preview.client.ts` 负责在 iframe 中保持 `preview=true` 查询参数，
> 新文件 `preview-bridge.client.ts` 独立负责预览桥接，两者互不干扰。

### 4.2 核心逻辑

```ts
// portal-web/app/plugins/preview-bridge.client.ts

/**
 * DIY 预览桥接插件
 *
 * 在 iframe 预览模式下（URL 含 ?preview=true），与父窗口 Admin 通信：
 * - 接收元素选择指令、样式应用指令、站点配置指令
 * - 上报选中元素的 CSS 属性
 */
export default defineNuxtPlugin(() => {
  // 1. 判断是否在 iframe 中 + URL 是否含 preview=true
  if (typeof window === 'undefined') return;
  const isInIframe = (() => {
    try { return window.top !== window.self; }
    catch { return false; }
  })();
  if (!isInIframe) return;

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('preview') !== 'true') return;

  const PARENT_ORIGIN = '*'; // 同域，允许宽松 origin

  // 2. 发送就绪信号
  window.parent.postMessage({ type: 'marvis:bridge-ready' }, PARENT_ORIGIN);

  // 3. 状态管理
  let selecting = false;
  let selectedElement: HTMLElement | null = null;
  let hoverElement: HTMLElement | null = null;

  // 存储所有已应用过样式的元素和其初始 style 快照，用于还原
  const styleSnapshots = new Map<HTMLElement, string | null>();

  // ================== 4. 元素选择模式 ==================

  function buildSelector(el: HTMLElement): string {
    // 构建唯一 CSS 选择器：优先使用 id，否则用 tag + classes + nth-child
    if (el.id) return `#${CSS.escape(el.id)}`;
    const parts: string[] = [];
    let current: HTMLElement | null = el;
    while (current && current !== document.body && current !== document.documentElement) {
      let seg = current.tagName.toLowerCase();
      if (current.classList.length > 0) {
        seg += '.' + Array.from(current.classList).map(c => CSS.escape(c)).join('.');
      }
      // 添加 nth-child 以保证唯一性
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          c => c.tagName === current!.tagName
        );
        if (siblings.length > 1) {
          const idx = siblings.indexOf(current) + 1;
          seg += `:nth-child(${idx})`;
        }
      }
      parts.unshift(seg);
      current = current.parentElement;
    }
    return parts.join(' > ');
  }

  function extractComputedStyles(el: HTMLElement) {
    const s = window.getComputedStyle(el);
    return {
      color: s.color,
      backgroundColor: s.backgroundColor,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      fontFamily: s.fontFamily,
      textAlign: s.textAlign,
      lineHeight: s.lineHeight,
      letterSpacing: s.letterSpacing,
      padding: s.padding,
      paddingTop: s.paddingTop,
      paddingRight: s.paddingRight,
      paddingBottom: s.paddingBottom,
      paddingLeft: s.paddingLeft,
      margin: s.margin,
      marginTop: s.marginTop,
      marginRight: s.marginRight,
      marginBottom: s.marginBottom,
      marginLeft: s.marginLeft,
      border: s.border,
      borderRadius: s.borderRadius,
      borderWidth: s.borderWidth,
      borderColor: s.borderColor,
      borderStyle: s.borderStyle,
      width: s.width,
      height: s.height,
      maxWidth: s.maxWidth,
      opacity: s.opacity,
      display: s.display,
      flexDirection: s.flexDirection,
      justifyContent: s.justifyContent,
      alignItems: s.alignItems,
      gap: s.gap,
      boxShadow: s.boxShadow,
      cursor: s.cursor
    };
  }

  function reportSelected(el: HTMLElement) {
    const rect = el.getBoundingClientRect();
    window.parent.postMessage({
      type: 'marvis:element-selected',
      payload: {
        selector: buildSelector(el),
        tag: el.tagName,
        id: el.id || '',
        classes: Array.from(el.classList),
        textContent: (el.textContent || '').trim().slice(0, 100),
        rect: {
          top: Math.round(rect.top),
          left: Math.round(rect.left),
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        },
        computedStyles: extractComputedStyles(el)
      }
    }, PARENT_ORIGIN);
  }

  // hover 高亮
  function onHover(e: MouseEvent) {
    if (!selecting) return;
    let target = e.target as HTMLElement | null;
    // 跳过 body/html 和我们自己的浮层
    while (target && (
      target === document.body ||
      target === document.documentElement ||
      target.classList.contains('marvis-preview-overlay')
    )) {
      target = target.parentElement;
    }
    if (!target || target === selectedElement) {
      clearHover();
      return;
    }
    if (hoverElement && hoverElement !== target) {
      hoverElement.style.outline = hoverElement.dataset.__marvisOrigOutline || '';
      hoverElement.style.outlineOffset = hoverElement.dataset.__marvisOrigOutlineOffset || '';
    }
    hoverElement = target;
    target.dataset.__marvisOrigOutline = target.style.outline;
    target.dataset.__marvisOrigOutlineOffset = target.style.outlineOffset;
    target.style.outline = '2px solid #ef4444';
    target.style.outlineOffset = '0px';
    e.stopPropagation();
  }

  function clearHover() {
    if (hoverElement) {
      hoverElement.style.outline = hoverElement.dataset.__marvisOrigOutline || '';
      hoverElement.style.outlineOffset = hoverElement.dataset.__marvisOrigOutlineOffset || '';
      delete hoverElement.dataset.__marvisOrigOutline;
      delete hoverElement.dataset.__marvisOrigOutlineOffset;
      hoverElement = null;
    }
  }

  // 点击选中
  function onClick(e: MouseEvent) {
    if (!selecting) return;
    let target = e.target as HTMLElement | null;
    while (target && (
      target === document.body ||
      target === document.documentElement ||
      target.classList.contains('marvis-preview-overlay')
    )) {
      target = target.parentElement;
    }
    if (!target) {
      deselect();
      return;
    }
    e.preventDefault();
    e.stopPropagation();

    // 清除旧选中
    if (selectedElement && selectedElement !== target) {
      selectedElement.style.outline = selectedElement.dataset.__marvisOrigOutline || '';
      selectedElement.style.outlineOffset = selectedElement.dataset.__marvisOrigOutlineOffset || '';
      delete selectedElement.dataset.__marvisOrigOutline;
      delete selectedElement.dataset.__marvisOrigOutlineOffset;
    }

    selectedElement = target;
    target.dataset.__marvisOrigOutline = target.style.outline;
    target.dataset.__marvisOrigOutlineOffset = target.style.outlineOffset;
    target.style.outline = '3px solid #10b981';
    target.style.outlineOffset = '1px';
    clearHover();

    reportSelected(target);
  }

  function deselect() {
    if (selectedElement) {
      selectedElement.style.outline = selectedElement.dataset.__marvisOrigOutline || '';
      selectedElement.style.outlineOffset = selectedElement.dataset.__marvisOrigOutlineOffset || '';
      delete selectedElement.dataset.__marvisOrigOutline;
      delete selectedElement.dataset.__marvisOrigOutlineOffset;
      selectedElement = null;
    }
    window.parent.postMessage({ type: 'marvis:element-deselected' }, PARENT_ORIGIN);
  }

  // 点击空白区域取消选中
  document.addEventListener('click', (e) => {
    if (!selecting) return;
    if (e.target === document.body || e.target === document.documentElement) {
      deselect();
    }
  }, true);

  // ================== 5. 应用样式 ==================

  function applyStyles(selector: string, styles: Record<string, string>) {
    const els = document.querySelectorAll(selector);
    els.forEach((el) => {
      const htmlEl = el as HTMLElement;
      // 首次应用时快照当前内联 style
      if (!styleSnapshots.has(htmlEl)) {
        styleSnapshots.set(htmlEl, htmlEl.getAttribute('style'));
      }
      Object.entries(styles).forEach(([key, val]) => {
        htmlEl.style[key as any] = val;
      });
    });
  }

  function revertStyles(selector: string) {
    const els = document.querySelectorAll(selector);
    els.forEach((el) => {
      const htmlEl = el as HTMLElement;
      const snapshot = styleSnapshots.get(htmlEl);
      if (snapshot === null) {
        htmlEl.removeAttribute('style');
      } else if (snapshot !== undefined) {
        htmlEl.setAttribute('style', snapshot);
      }
      styleSnapshots.delete(htmlEl);
    });
  }

  // ================== 6. 站点配置注入 ==================

  function applySiteConfig(config: any) {
    const root = document.documentElement;
    // 注入 CSS 变量
    if (config.theme) {
      const t = config.theme;
      if (t.primaryColor) root.style.setProperty('--color-primary', t.primaryColor);
      if (t.primaryLight) root.style.setProperty('--color-primary-light', t.primaryLight);
      if (t.primaryDark) root.style.setProperty('--color-primary-dark', t.primaryDark);
      if (t.secondaryColor) root.style.setProperty('--color-secondary', t.secondaryColor);
      if (t.accentColor) root.style.setProperty('--color-accent', t.accentColor);
      if (t.fontHeading) root.style.setProperty('--font-heading', t.fontHeading);
      if (t.fontBody) root.style.setProperty('--font-body', t.fontBody);
    }
    // 品牌名称 - 尝试更新页面中 logo 文字或 header 品牌名
    if (config.brand?.name) {
      const brandEls = document.querySelectorAll('[data-brand-name], .brand-name, .logo-text');
      brandEls.forEach(el => { el.textContent = config.brand.name; });
    }
    // 版权
    if (config.footer?.copyright) {
      const copyrightEls = document.querySelectorAll('.copyright, [data-copyright]');
      copyrightEls.forEach(el => { el.textContent = config.footer.copyright; });
    }
    // 导航 - 仅实时预览，不持久化；刷新页面后恢复
    if (Array.isArray(config.nav) && config.nav.length > 0) {
      // 寻找页面中的导航列表（尝试 header nav ul 等常见结构）
      const navContainer = document.querySelector('header nav ul, .main-nav, [data-nav]');
      if (navContainer) {
        navContainer.innerHTML = config.nav.map(
          (item: any) => `<li><a href="${item.url || '#'}">${item.label || ''}</a></li>`
        ).join('');
      }
    }
  }

  // ================== 7. 消息监听 ==================

  window.addEventListener('message', (event) => {
    // origin 校验：同域可放宽，但确保是父窗口
    if (event.source !== window.parent) return;

    const msg = event.data;
    if (!msg || typeof msg.type !== 'string') return;

    switch (msg.type) {
      case 'marvis:start-select':
        selecting = true;
        document.body.style.cursor = 'crosshair';
        document.addEventListener('mouseover', onHover, true);
        document.addEventListener('click', onClick, true);
        break;

      case 'marvis:stop-select':
        selecting = false;
        document.body.style.cursor = '';
        clearHover();
        deselect();
        document.removeEventListener('mouseover', onHover, true);
        document.removeEventListener('click', onClick, true);
        break;

      case 'marvis:apply-styles':
        if (msg.payload?.selector && msg.payload?.styles) {
          applyStyles(msg.payload.selector, msg.payload.styles);
        }
        break;

      case 'marvis:revert-styles':
        if (msg.payload?.selector) {
          revertStyles(msg.payload.selector);
        }
        break;

      case 'marvis:apply-config':
        if (msg.payload) {
          applySiteConfig(msg.payload);
        }
        break;
    }
  });
});
```

### 4.3 CSS 类定义

在 Nuxt 项目中不需要额外 CSS 文件——所有视觉反馈通过内联 style 实现：
- hover: `outline: 2px solid #ef4444` (红色虚线高亮)
- selected: `outline: 3px solid #10b981` (绿色实线选中)
- selecting mode: `body style.cursor = 'crosshair'`

---

## 5. A 侧实现

### 5.1 Store 改动

文件：`admin/src/store/modules/diy/index.ts`

在 return 对象中新增以下状态和方法：

```ts
// ========== 元素选择模式状态 ==========

/** 元素选择模式开关 */
const elementSelectMode = ref(false);

/** 当前选中的 iframe 元素信息 */
const selectedElement = ref<{
  selector: string;
  tag: string;
  id: string;
  classes: string[];
  textContent: string;
  rect: { top: number; left: number; width: number; height: number };
  computedStyles: Record<string, string>;
} | null>(null);

/** B 侧桥接是否就绪 */
const bridgeReady = ref(false);

function setElementSelectMode(v: boolean) {
  elementSelectMode.value = v;
}

function setSelectedElement(el: typeof selectedElement.value) {
  selectedElement.value = el;
  // 选择元素时取消组件选中和站点配置选中
  if (el) {
    activeComponentId.value = null;
    activeSiteConfigItem.value = null;
  }
}

function setBridgeReady(v: boolean) {
  bridgeReady.value = v;
}
```

在 return 对象中追加导出：

```ts
elementSelectMode,
selectedElement,
bridgeReady,
setElementSelectMode,
setSelectedElement,
setBridgeReady,
```

### 5.2 diy/index.vue 改动

文件：`admin/src/views/diy/index.vue`

#### 5.2.1 替换元素选择模式实现

**删除**现有所有 DOM 注入代码（约 150 行），包括：
- 函数 `createMarvisFloatButton`
- 函数 `removeMarvisFloatButton`
- 函数 `updateMarvisFloatTip`
- 函数 `installMarvisOnDoc`
- 函数 `installIframeSelection`
- 函数 `installCanvasSelection`
- 函数 `enableElementSelection`
- 函数 `disableElementSelection`
- 变量 `globalMarvisCleanup, canvasMarvisCleanup, marvisFloatEl`

**替换为**以下 postMessage 通信实现：

```ts
// ========== postMessage 元素选择桥接 ==========

/** 向 iframe 发送消息 */
function postToIframe(msg: { type: string; payload?: any }) {
  const iframe = iframeRef.value;
  if (!iframe?.contentWindow) return;
  iframe.contentWindow.postMessage(msg, '*');
}

/** 接收来自 iframe (B) 的消息 */
function handleBridgeMessage(event: MessageEvent) {
  // 只处理来自 iframe 的消息
  if (event.source !== iframeRef.value?.contentWindow) return;
  const msg = event.data;
  if (!msg || typeof msg.type !== 'string') return;

  switch (msg.type) {
    case 'marvis:bridge-ready':
      store.setBridgeReady(true);
      // 如果选择模式已开启，补发 start-select
      if (store.elementSelectMode) {
        postToIframe({ type: 'marvis:start-select' });
      }
      break;
    case 'marvis:element-selected':
      store.setSelectedElement(msg.payload);
      break;
    case 'marvis:element-deselected':
      store.setSelectedElement(null);
      break;
  }
}

/** 模式切换 */
function toggleElementSelect() {
  const newVal = !store.elementSelectMode;
  store.setElementSelectMode(newVal);
  if (newVal) {
    postToIframe({ type: 'marvis:start-select' });
  } else {
    postToIframe({ type: 'marvis:stop-select' });
    store.setSelectedElement(null);
  }
}
```

#### 5.2.2 iframe 加载时绑定消息监听

修改 `onIframeLoad`，在现有逻辑末尾追加：

```ts
// 在 onIframeLoad 末尾：
// 绑定 postMessage 监听（每次 iframe src 变更时重新绑定）
window.addEventListener('message', handleBridgeMessage);

// 如果选择模式已开启，向 iframe 发送指令
if (store.elementSelectMode) {
  postToIframe({ type: 'marvis:start-select' });
}

// 如果站点配置已加载，注入到 iframe
if (store.siteConfig) {
  postToIframe({ type: 'marvis:apply-config', payload: { ...store.siteConfig } });
}
```

#### 5.2.3 iframeKey 联动策略

当以下条件触发时，需要重建 iframe（递增 `iframeKey`）：
- 用户从 canvas 模式切回 preview 模式时（需要刷新组件变更）
- 用户发布页面后，cut 回该 tab 时
- 不需要重建的场景：
  - 站点配置修改（通过 postMessage 实时注入）
  - 元素样式修改（通过 postMessage 实时应用）
  - 元素选择模式切换

```ts
// 预览模式切回时重建 iframe（watch mode 中已有逻辑，增强即可）
watch(mode, (newMode) => {
  if (newMode === 'preview') {
    // 从 canvas 切回预览时重建 iframe 以反映组件变更
    nextTick(() => {
      iframeKey.value++;
    });
    startIframeUrlPolling();
  } else {
    stopIframeUrlPolling();
    // 关闭选择模式
    if (store.elementSelectMode) {
      postToIframe({ type: 'marvis:stop-select' });
    }
  }
});
```

#### 5.2.4 组件卸载清理

修改 `onUnmounted`：

```ts
onUnmounted(() => {
  window.removeEventListener('message', handleBridgeMessage);
  stopIframeUrlPolling();
  postToIframe({ type: 'marvis:stop-select' });
  store.reset();
});
```

#### 5.2.5 站点配置保存后实时注入

在 `handleSaveSiteConfig` 相关逻辑中，站点配置保存后：

```ts
async function handleSaveSiteConfig() {
  // ... 保存逻辑 ...
  // 保存成功后实时推送到 iframe
  postToIframe({ type: 'marvis:apply-config', payload: { ...store.siteConfig } });
}
```

> 注意：`handleSaveSiteConfig` 位于 `PropertyPanel.vue`，需从该组件触发或在 store 中添加 `saveSiteConfig` 的副作用。

### 5.3 PropertyPanel.vue 改动

文件：`admin/src/views/diy-editor/modules/PropertyPanel.vue`

#### 5.3.1 新增「选中元素」区块

在现有 template 的 `<template v-if="component">` 之前插入：

```html
<!-- 选中元素（预览模式 + 元素选择模式下选中了 iframe 中的元素） -->
<template v-if="store.selectedElement">
  <div class="mb-4 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
    <div class="mb-3 flex items-center gap-2">
      <SvgIcon icon="mdi:cursor-default-click" class="text-18px text-purple-600" />
      <span class="font-semibold truncate text-sm" :title="store.selectedElement.selector">
        {{ store.selectedElement.tag.toLowerCase() }}{{ store.selectedElement.id ? '#' + store.selectedElement.id : '' }}
      </span>
      <NButton size="tiny" quaternary type="error" class="ml-auto" @click="deselectElement">
        <template #icon><SvgIcon icon="mdi:close" /></template>
      </NButton>
    </div>
    <div class="mb-2 text-xs text-gray-400 truncate" :title="store.selectedElement.selector">
      选择器：{{ store.selectedElement.selector }}
    </div>
    <div v-if="store.selectedElement.textContent" class="mb-2 text-xs text-gray-400 truncate">
      文本：{{ store.selectedElement.textContent }}
    </div>
  </div>

  <!-- CSS 属性编辑 -->
  <div class="flex flex-col gap-3 max-h-[calc(100vh-400px)] overflow-y-auto">
    <!-- 文字样式 -->
    <NCollapse :default-expanded-names="['typography', 'spacing', 'visual']">
      <NCollapseItem name="typography">
        <template #header>
          <span class="text-xs font-semibold">文字样式</span>
        </template>
        <div class="flex flex-col gap-2 pl-2">
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">颜色</span>
            <NColorPicker
              size="small"
              :value="selectedStyles.color"
              @update:value="v => applyStyle('color', v)"
            />
            <NInput
              size="small"
              :value="selectedStyles.color"
              @update:value="v => applyStyle('color', v)"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">字号</span>
            <NInputNumber
              size="small"
              :value="parseFloat(selectedStyles.fontSize)"
              @update:value="v => applyStyle('fontSize', v + 'px')"
              style="flex:1"
            />
            <span class="text-xs text-gray-400">px</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">字重</span>
            <NSelect
              size="small"
              :value="selectedStyles.fontWeight"
              :options="fontWeightOptions"
              @update:value="v => applyStyle('fontWeight', v)"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">字体</span>
            <NInput
              size="small"
              :value="selectedStyles.fontFamily"
              @update:value="v => applyStyle('fontFamily', v)"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">对齐</span>
            <NSelect
              size="small"
              :value="selectedStyles.textAlign"
              :options="textAlignOptions"
              @update:value="v => applyStyle('textAlign', v)"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">行高</span>
            <NInput
              size="small"
              :value="selectedStyles.lineHeight"
              @update:value="v => applyStyle('lineHeight', v)"
              style="flex:1"
            />
          </div>
        </div>
      </NCollapseItem>

      <!-- 间距 -->
      <NCollapseItem name="spacing">
        <template #header>
          <span class="text-xs font-semibold">间距</span>
        </template>
        <div class="flex flex-col gap-2 pl-2">
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">内边距</span>
            <NInput size="small" :value="selectedStyles.padding" @update:value="v => applyStyle('padding', v)" style="flex:1" placeholder="上 右 下 左" />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">外边距</span>
            <NInput size="small" :value="selectedStyles.margin" @update:value="v => applyStyle('margin', v)" style="flex:1" placeholder="上 右 下 左" />
          </div>
        </div>
      </NCollapseItem>

      <!-- 视觉 -->
      <NCollapseItem name="visual">
        <template #header>
          <span class="text-xs font-semibold">视觉</span>
        </template>
        <div class="flex flex-col gap-2 pl-2">
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">背景色</span>
            <NColorPicker
              size="small"
              :value="selectedStyles.backgroundColor"
              @update:value="v => applyStyle('backgroundColor', v)"
            />
            <NInput
              size="small"
              :value="selectedStyles.backgroundColor"
              @update:value="v => applyStyle('backgroundColor', v)"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">圆角</span>
            <NInputNumber
              size="small"
              :value="parseFloat(selectedStyles.borderRadius)"
              @update:value="v => applyStyle('borderRadius', v + 'px')"
              style="flex:1"
            />
            <span class="text-xs text-gray-400">px</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">透明度</span>
            <NInputNumber
              size="small"
              :value="parseFloat(selectedStyles.opacity)"
              :min="0"
              :max="1"
              :step="0.05"
              @update:value="v => applyStyle('opacity', String(v))"
              style="flex:1"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="w-16 shrink-0 text-xs text-gray-400">阴影</span>
            <NInput
              size="small"
              :value="selectedStyles.boxShadow"
              @update:value="v => applyStyle('boxShadow', v)"
              style="flex:1"
            />
          </div>
        </div>
      </NCollapseItem>
    </NCollapse>

    <NDivider class="!my-2" />
    <div class="flex gap-2">
      <NButton size="small" quaternary type="warning" block @click="resetElementStyles">
        重置样式
      </NButton>
    </div>
  </div>
</template>

<!-- 原有的组件属性面板 / 站点配置面板 / 空状态继续保留 -->
<template v-else-if="component">
  <!-- ... 不变 ... -->
</template>
```

#### 5.3.2 脚本部分新增

在 `<script setup>` 中追加：

```ts
import { NCollapse, NCollapseItem, NDivider, NInputNumber } from 'naive-ui';

// 选中元素的可编辑样式（响应式，可直接编辑）
const selectedStyles = computed(() => {
  const el = store.selectedElement;
  if (!el) return {};
  // 直接返回 computedStyles 的浅拷贝，用于 v-model 绑定
  return { ...el.computedStyles };
});

const fontWeightOptions = [
  { label: 'Thin (100)', value: '100' },
  { label: 'Light (300)', value: '300' },
  { label: 'Normal (400)', value: '400' },
  { label: 'Medium (500)', value: '500' },
  { label: 'Semibold (600)', value: '600' },
  { label: 'Bold (700)', value: '700' },
  { label: 'Extrabold (800)', value: '800' },
  { label: 'Black (900)', value: '900' }
];

const textAlignOptions = [
  { label: '左对齐', value: 'left' },
  { label: '居中', value: 'center' },
  { label: '右对齐', value: 'right' },
  { label: '两端对齐', value: 'justify' }
];

/** 获取 iframe 引用并发消息 */
function postToIframe(msg: { type: string; payload?: any }) {
  // 通过 window.parent 获取（本组件在 admin 的 diy/index.vue 中被引用，
  // 而 iframe 是 diy/index.vue 中的 ref，这里通过自定义事件或直接访问 iframe）
  // 方案：使用自定义事件，由 diy/index.vue 监听
  window.dispatchEvent(new CustomEvent('marvis:property-panel-action', { detail: msg }));
}

function applyStyle(key: string, value: string) {
  if (!store.selectedElement) return;
  postToIframe({
    type: 'marvis:apply-styles',
    payload: {
      selector: store.selectedElement.selector,
      styles: { [key]: value }
    }
  });
}

function resetElementStyles() {
  if (!store.selectedElement) return;
  postToIframe({
    type: 'marvis:revert-styles',
    payload: { selector: store.selectedElement.selector }
  });
}

function deselectElement() {
  store.setSelectedElement(null);
  // 通知 iframe 停止选中高亮
  postToIframe({ type: 'marvis:stop-select' });
  // 重新开启选择模式（保持选择模式开启，只是取消当前选中）
  setTimeout(() => {
    postToIframe({ type: 'marvis:start-select' });
  }, 100);
}
```

#### 5.3.3 diy/index.vue 桥接事件监听

在 `diy/index.vue` 中补充：

```ts
// 监听 PropertyPanel 发来的 postMessage 请求
function handlePropertyPanelAction(e: CustomEvent) {
  if (e.detail?.type) {
    postToIframe(e.detail);
  }
}

// onMounted 中：
window.addEventListener('marvis:property-panel-action', handlePropertyPanelAction as EventListener);

// onUnmounted 中：
window.removeEventListener('marvis:property-panel-action', handlePropertyPanelAction as EventListener);
```

---

## 6. 完整交互流程

### 6.1 元素选择闭环

```
1. 用户: 点击「元素选择」按钮
2. diy/index.vue: toggleElementSelect() → store.elementSelectMode = true
                → postToIframe({ type: 'marvis:start-select' })
3. B preview-bridge: 收到 start-select → selecting = true → body cursor=crosshair
                   → 添加 mouseover/click 监听
4. 用户: 在 iframe 中移动鼠标 → hover 元素出现红色虚线框
5. 用户: 点击某个元素 → 绿色实线选中
6. B preview-bridge: onClick → reportSelected(el)
                    → postMessage({ type: 'marvis:element-selected', payload: {...} })
7. diy/index.vue: handleBridgeMessage → store.setSelectedElement(payload)
8. PropertyPanel: 响应式更新 → 显示选中元素区块
                 → 展示 selector + 可编辑 CSS 属性
9. 用户: 在 PropertyPanel 修改背景色 → applyStyle('backgroundColor', '#ff0000')
      → postToIframe({ type: 'marvis:apply-styles', payload: { selector, styles: {...} } })
10. B preview-bridge: applyStyles → querySelector → el.style.backgroundColor = '#ff0000'
11. 用户: 即时看到 iframe 中元素的背景色变为红色
```

### 6.2 站点配置闭环

```
1. 用户: 在左侧面板选择「主题」站点配置
2. PropertyPanel: 显示主题色/字体配置
3. 用户: 修改主色 → on change 实时推送：
   postToIframe({ type: 'marvis:apply-config', payload: { theme: { primaryColor: '#ff0000' } } })
4. B preview-bridge: applySiteConfig → document.documentElement.style.setProperty('--color-primary', '#ff0000')
5. 用户: 点击「保存站点配置」→ store.saveSiteConfig() → 持久化到后端
```

### 6.3 模式切换闭环

```
canvas → preview:
  1. mode 变为 'preview'
  2. iframeKey++ 重建 iframe（反映组件变更）
  3. startIframeUrlPolling()
  4. 如果元素选择模式之前开启 → iframe load 后补发 start-select

preview → canvas:
  1. mode 变为 'canvas'
  2. stopIframeUrlPolling()
  3. 如果元素选择模式开启 → postToIframe({ type: 'marvis:stop-select' })
  4. store.setSelectedElement(null)
```

---

## 7. 注意事项

### 7.1 同域保证

当前部署架构中，`/portal-preview/zh/` 被 nginx 反向代理到 localhost:3000（Nuxt），因此 A 和 B 同域。`postMessage` 的 `targetOrigin` 使用 `'*'` 是安全的，也可改为 `window.location.origin`。

`diy/index.vue` 中 iframe 的 `sandbox` 属性必须包含 `allow-scripts` 和 `allow-same-origin`，目前已是如此。

### 7.2 选择器唯一性

`buildSelector` 通过 `nth-child` 保证 CSS 选择器在同级子元素中唯一，但无法保证在整个文档中唯一。如果用户选中了列表中的某一项（如 `.product-card:nth-child(3)`），`apply-styles` 会对所有 `.product-card:nth-child(3)` 生效——但每个父元素下只有一个 `nth-child(3)`，所以实际上是安全的。

如果未来出现同一选择器匹配多个元素的需求，可以在 `element-selected` 中增加一个 UUID 属性 `data-marvis-elid` 到元素上，用属性选择器精确定位。

### 7.3 样式还原策略

`revert-styles` 恢复第一次应用样式前的内联 style 快照，但不恢复 CSS 文件/样式表中的样式（那些从未被修改）。如果用户修改了原本由 CSS 文件设置的属性（如 `color`），还原后会恢复到 CSS 文件的定义（因为内联 style 被移除）。

### 7.4 iframe SPA 导航

当用户在 iframe 中点击链接（Nuxt SPA 导航），iframe 会重新加载页面。此时 B 的 `preview-bridge.client.ts` 会重新初始化，向 A 发送新的 `bridge-ready`。A 需要重新发送 `start-select`（如果选择模式开启）和 `apply-config`（保持站点配置注入）。

这个逻辑已在 5.2.2 节的 `onIframeLoad` 中处理。

已有的 `diy-preview.client.ts` 确保 SPA 导航时 `preview=true` 查询参数不会丢失，使得新的 `preview-bridge.client.ts` 能正常激活。

### 7.5 性能

- 选择模式下的 `mouseover` 事件使用捕获阶段 (`true`)，不会影响页面正常交互
- `extractComputedStyles` 只提取 30 个关键 CSS 属性，而非全部 300+ 个，避免序列化臃肿
- `apply-styles` 直接修改内联 style，浏览器重绘开销极小

---

## 8. 测试验证清单

### 8.1 元素选择模式

- [ ] 开启元素选择模式 → iframe 中 body 光标变为 crosshair
- [ ] 鼠标悬浮元素 → 红色虚线框出现
- [ ] 鼠标移出 → 红色虚线框消失
- [ ] 点击元素 → 绿色实线框固定 → A 中 PropertyPanel 显示选中元素信息
- [ ] 点击 iframe 空白区域 → 取消选中 → PropertyPanel 回到空状态
- [ ] 关闭元素选择模式 → iframe 恢复默认光标 → 所有高亮清除

### 8.2 CSS 属性编辑

- [ ] 修改颜色 → iframe 中元素颜色即时变化
- [ ] 修改字号 → iframe 中元素字号即时变化
- [ ] 修改背景色 → iframe 中元素背景色即时变化
- [ ] 修改多个属性 → 全部生效，无互相覆盖
- [ ] 点击「重置样式」→ iframe 中元素恢复原始样式

### 8.3 站点配置注入

- [ ] 修改主题色 → iframe 中 CSS 变量被注入，页面颜色变化
- [ ] 修改品牌名称 → iframe 中 header 品牌名更新
- [ ] 保存站点配置 → 持久化 + iframe 保持注入状态
- [ ] iframe SPA 导航后（点击页面链接）→ 站点配置仍被注入

### 8.4 模式切换

- [ ] canvas → preview 切换 → iframe 重建，组件变更可见
- [ ] preview → canvas 切换 → 元素选择自动关闭
- [ ] 切换过程中元素选择模式状态正确同步

### 8.5 边界情况

- [ ] 选中 body 元素 → 不报错，正常显示属性
- [ ] 快速多次切换元素选择模式 → 无状态错乱
- [ ] iframe 加载中开启选择模式 → bridge-ready 后自动恢复
- [ ] 浏览器后退/前进 → 不影响功能
- [ ] 同时打开多个 tab → 切换 tab 后元素选择重新安装

---

## 9. 文件变更清单

| # | 文件 | 操作 | 预估行数 |
|---|------|------|----------|
| 1 | `portal-web/app/plugins/preview-bridge.client.ts` | **新建** | ~200 行 |
| 2 | `admin/src/store/modules/diy/index.ts` | **修改** | +40 行（新增状态 + actions） |
| 3 | `admin/src/views/diy/index.vue` | **修改** | -150 行（删旧注入代码）+80 行（新 postMessage 代码） |
| 4 | `admin/src/views/diy-editor/modules/PropertyPanel.vue` | **修改** | +120 行（新增选中元素区块） |

---

*最后更新：2026-08-11*
*（内容由AI生成，仅供参考）*
