const local: App.I18n.Schema = {
  system: {
    title: 'Forge 管理系统',
    updateTitle: '系统版本更新通知',
    updateContent: '检测到系统有新版本发布，是否立即刷新页面？',
    updateConfirm: '立即刷新',
    updateCancel: '稍后再说'
  },
  common: {
    action: '操作',
    add: '新增',
    addSuccess: '添加成功',
    backToHome: '返回首页',
    batchDelete: '批量删除',
    cancel: '取消',
    close: '关闭',
    check: '勾选',
    selectAll: '全选',
    expandColumn: '展开列',
    columnSetting: '列设置',
    config: '配置',
    confirm: '确认',
    delete: '删除',
    deleteSuccess: '删除成功',
    confirmDelete: '确认删除吗？',
    save: '保存',
    name: '名称',
    status: '状态',
    type: '类型',
    region: '区域',
    regions: '适用区域',
    priority: '优先级',
    active: '启用',
    inactive: '未启用',
    default: '默认',
    start: '开始',
    end: '结束',
    calculate: '计算',
    detail: '详情',
    view: '查看',
    yes: '是',
    no: '否',
    adopted: '已采纳',
    notAdopted: '未采纳',
    conversation: '对话',
    messages: '消息',
    userId: '用户 ID',
    started: '开始时间',
    items: '商品数量',
    created: '创建时间',
    enforce: '强制',
    language: '语言',
    regionsComma: '适用区域（逗号分隔）',
    categoriesComma: '分类（逗号分隔）',
    basicInfo: '基本信息',
    tagsRegions: '标签与区域',
    productImages: '商品图片',
    uploadImages: '上传图片',
    dangerZone: '危险区域',
    loadFailed: '加载失败',
    uploadFailed: '上传失败',
    deleteFailed: '删除失败',
    saveFailed: '保存失败',
    quantity: '数量',
    backToList: '返回列表',
    image: '图片',
    inventory: '库存',
    cost: '成本',
    description: '描述',
    product: '商品',
    new: '新建',
    sku: 'SKU',
    origin: '出发地',
    destination: '目的地',
    period: '有效期',
    carrier: '物流商',
    edit: '编辑',
    warning: '警告',
    error: '错误',
    index: '序号',
    keywordSearch: '请输入关键词搜索',
    logout: '退出登录',
    logoutConfirm: '确认退出登录吗？',
    lookForward: '敬请期待',
    modify: '修改',
    modifySuccess: '修改成功',
    noData: '无数据',
    publish: '发布',
    saveDraft: '保存草稿',
    operate: '操作',
    pleaseCheckValue: '请检查输入的值是否合法',
    refresh: '刷新',
    reset: '重置',
    search: '搜索',
    switch: '切换',
    tip: '提示',
    trigger: '触发',
    update: '更新',
    updateSuccess: '更新成功',
    userCenter: '个人中心',
    yesOrNo: {
      yes: '是',
      no: '否'
    }
  },
  request: {
    logout: '请求失败后登出用户',
    logoutMsg: '用户状态失效，请重新登录',
    logoutWithModal: '请求失败后弹出模态框再登出用户',
    logoutWithModalMsg: '用户状态失效，请重新登录',
    refreshToken: '请求的token已过期，刷新token',
    tokenExpired: 'token已过期'
  },
  theme: {
    themeDrawerTitle: '主题配置',
    tabs: {
      appearance: '外观',
      layout: '布局',
      general: '通用',
      preset: '预设'
    },
    appearance: {
      themeSchema: {
        title: '主题模式',
        light: '亮色模式',
        dark: '暗黑模式',
        auto: '跟随系统'
      },
      grayscale: '灰色模式',
      colourWeakness: '色弱模式',
      themeColor: {
        title: '主题颜色',
        primary: '主色',
        info: '信息色',
        success: '成功色',
        warning: '警告色',
        error: '错误色',
        followPrimary: '跟随主色'
      },
      themeRadius: {
        title: '主题圆角'
      },
      recommendColor: '应用推荐算法的颜色',
      recommendColorDesc: '推荐颜色的算法参照',
      preset: {
        title: '主题预设',
        apply: '应用',
        applySuccess: '预设应用成功',
        default: {
          name: '默认预设',
          desc: 'Forge 默认主题预设'
        },
        dark: {
          name: '暗色预设',
          desc: '适用于夜间使用的暗色主题预设'
        },
        compact: {
          name: '紧凑型',
          desc: '适用于小屏幕的紧凑布局预设'
        },
        azir: {
          name: 'Azir的预设',
          desc: '是 Azir 比较喜欢的莫兰迪色系冷淡风'
        }
      }
    },
    layout: {
      layoutMode: {
        title: '布局模式',
        vertical: '左侧菜单模式',
        'vertical-mix': '左侧菜单混合模式',
        'vertical-hybrid-header-first': '左侧混合-顶部优先',
        horizontal: '顶部菜单模式',
        'top-hybrid-sidebar-first': '顶部混合-侧边优先',
        'top-hybrid-header-first': '顶部混合-顶部优先',
        vertical_detail: '左侧菜单布局，菜单在左，内容在右。',
        'vertical-mix_detail': '左侧双菜单布局，一级菜单在左侧深色区域，二级菜单在左侧浅色区域。',
        'vertical-hybrid-header-first_detail':
          '左侧混合布局，一级菜单在顶部，二级菜单在左侧深色区域，三级菜单在左侧浅色区域。',
        horizontal_detail: '顶部菜单布局，菜单在顶部，内容在下方。',
        'top-hybrid-sidebar-first_detail': '顶部混合布局，一级菜单在左侧，二级菜单在顶部。',
        'top-hybrid-header-first_detail': '顶部混合布局，一级菜单在顶部，二级菜单在左侧。'
      },
      tab: {
        title: '标签栏设置',
        visible: '显示标签栏',
        cache: '标签栏信息缓存',
        cacheTip: '离开页面后仍然保留标签栏信息',
        height: '标签栏高度',
        mode: {
          title: '标签栏风格',
          slider: '滑块风格',
          chrome: '谷歌风格',
          button: '按钮风格'
        },
        closeByMiddleClick: '鼠标中键关闭标签页',
        closeByMiddleClickTip: '启用后可以使用鼠标中键点击标签页进行关闭'
      },
      header: {
        title: '头部设置',
        height: '头部高度',
        breadcrumb: {
          visible: '显示面包屑',
          showIcon: '显示面包屑图标'
        }
      },
      sider: {
        title: '侧边栏设置',
        inverted: '深色侧边栏',
        width: '侧边栏宽度',
        collapsedWidth: '侧边栏折叠宽度',
        mixWidth: '混合布局侧边栏宽度',
        mixCollapsedWidth: '混合布局侧边栏折叠宽度',
        mixChildMenuWidth: '混合布局子菜单宽度',
        autoSelectFirstMenu: '自动选择第一个子菜单',
        autoSelectFirstMenuTip: '点击一级菜单时，自动选择并导航到第一个子菜单的最深层级'
      },
      footer: {
        title: '底部设置',
        visible: '显示底部',
        fixed: '固定底部',
        height: '底部高度',
        right: '底部居右'
      },
      content: {
        title: '内容区域设置',
        scrollMode: {
          title: '滚动模式',
          tip: '主题滚动仅 main 部分滚动，外层滚动可携带头部底部一起滚动',
          wrapper: '外层滚动',
          content: '主体滚动'
        },
        page: {
          animate: '页面切换动画',
          mode: {
            title: '页面切换动画类型',
            'fade-slide': '滑动',
            fade: '淡入淡出',
            'fade-bottom': '底部消退',
            'fade-scale': '缩放消退',
            'zoom-fade': '渐变',
            'zoom-out': '闪现',
            none: '无'
          }
        },
        fixedHeaderAndTab: '固定头部和标签栏'
      }
    },
    general: {
      title: '通用设置',
      watermark: {
        title: '水印设置',
        visible: '显示全屏水印',
        text: '自定义水印文本',
        enableUserName: '启用用户名水印',
        enableTime: '显示当前时间',
        timeFormat: '时间格式'
      },
      multilingual: {
        title: '多语言设置',
        visible: '显示多语言按钮'
      },
      globalSearch: {
        title: '全局搜索设置',
        visible: '显示全局搜索按钮'
      }
    },
    configOperation: {
      copyConfig: '复制配置',
      copySuccessMsg: '复制成功，请替换 src/theme/settings.ts 中的变量 themeSettings',
      resetConfig: '重置配置',
      resetSuccessMsg: '重置成功'
    }
  },
  route: {
    login: '登录',
    403: '无权限',
    404: '页面不存在',
    500: '服务器错误',
    'iframe-page': '外链页面',
    home: '首页',
    dashboard: '仪表盘',
    resources: '资源管理',
    merchandise: '商品管理',
    suppliers: '供应商',
    pricing: '定价',
    sales: '销售管理',
    shipments: '物流',
    products: '产品',
    'products-new': '新建产品',
    'products-detail': '编辑产品',
    orders: '订单',
    'orders-detail': '订单详情',
    'ai-probe': 'AI 探测',
    users: '用户',
    site: '站点',
    system: '系统管理',
    settings: '设置',
    customers: '客户',
    'admin-users': '管理员',
    roles: '角色管理',
    'site-config': '站点配置'
  },
  page: {
    dashboard: {
      todayOrders: '今日订单',
      pendingOrders: '待处理订单',
      todayGMV: '今日 GMV',
      activeProducts: '活跃商品',
      probeAdoption: 'AI 探测采纳率',
      procurementErrors: '采购异常',
      activeSuppliers: '活跃供应商',
      probeRequests: '探测请求',
      ordersTrend: '订单趋势（近7日）',
      productCategories: '商品分类'
    },
    suppliers: {
      contactEmail: '联系邮箱',
      contactPhone: '联系电话',
      defaultCurrency: '默认货币',
      integrationType: '集成类型',
      shippingRegions: '配送区域',
      supplierList: '供应商列表',
      addSupplier: '添加供应商',
      editSupplier: '编辑供应商',
      name: '名称',
      status: '状态',
      actions: '操作',
      active: '启用',
      inactive: '停用',
      address: '地址',
      noSupplier: '暂无供应商',
      provider: '厂商',
      providerCode: '厂商代码',
      providerCodePlaceholder: '选择货源厂商（仅新建时可改）',
      credentials: '凭据',
      accessToken: 'Access Token',
      tokenType: 'Token 类型',
      saveCredentials: '保存凭据',
      credSaved: '凭据已保存',
      credentialsMissing: '未配置凭据',
      searchProducts: '搜索货源',
      searchKeyword: '关键词',
      searchPlaceholder: '输入关键词搜索货源',
      search: '搜索',
      importSelected: '导入选中',
      noSearchResult: '暂无货源结果',
      price: '价格',
      inventory: '库存',
      imported: '已导入',
      failed: '失败',
      syncNow: '立即同步',
      syncLogs: '同步日志',
      syncStatus: '同步状态',
      triggerType: '触发方式',
      itemsTotal: '商品数',
      itemsImported: '新增',
      itemsUpdated: '更新',
      startedAt: '开始时间',
      finishedAt: '结束时间',
      noLogs: '暂无同步日志',
      syncing: '同步中...',
      syncDone: '同步完成',
      syncFailed: '同步失败',
      manual: '手动',
      scheduled: '定时',
      success: '成功',
      running: '进行中',
      partial: '部分成功',
      confirmImport: '确认导入选中的货源商品？',
      importResult: '导入完成：新增 {imported}，失败 {failed}'
    },
    pricing: {
      title: '定价',
      costPrice: '成本价',
      fixedShippingFee: '固定运费',
      markupMultiplier: '加价倍率',
      overridePrice: '覆盖价格（可选）',
      priceCalculator: '价格计算器',
      pricingRule: '定价规则',
      productId: '商品 ID（可选）',
      addRule: '添加规则',
      noRules: '暂无定价规则',
      promotions: '促销活动',
      noPromotions: '暂无促销活动',
      promoCount: '{count} 个促销活动',
      coupon: '优惠券',
      discount: '折扣',
      bundle: '捆绑'
    },
    shipments: {
      estimatedDelivery: '预计送达',
      orderId: '订单 ID',
      trackingNumber: '物流单号',
      shipmentList: '物流列表',
      noShipments: '暂无物流',
      carrier: '物流商',
      newShipment: '新建物流',
      editShipment: '编辑物流',
      eta: '预计到达'
    },
    products: {
      allCategories: '全部分类',
      productList: '商品列表',
      noProducts: '暂无商品',
      category: '分类',
      price: '价格',
      export: '导出',
      import: '导入',
      importResult: '导入结果',
      importCreated: '新增',
      importUpdated: '更新',
      importFailed: '失败',
      importRow: '行号',
      importError: '错误信息'
    },
    productsDetail: {
      aiGenerated: 'AI 生成',
      backToList: '返回列表',
      basicInfo: '基本信息',
      changeStatus: '更改状态',
      costUsd: '成本（美元）',
      dangerZone: '危险区域',
      priceUsd: '价格（美元）',
      productImages: '商品图片',
      regionsComma: '区域（逗号分隔）',
      saveProduct: '保存商品',
      tagsComma: '标签（逗号分隔）',
      updateStatus: '更新状态',
      uploadImages: '上传图片',
      editProduct: '编辑商品',
      slug: 'Slug',
      inventory: '库存',
      sku: 'SKU'
    },
    orders: {
      allStatus: '全部状态',
      orderList: '订单列表',
      noOrders: '暂无订单',
      orderNumber: '订单编号',
      total: '总计',
      date: '日期'
    },
    ordersDetail: {
      approve: '审核通过',
      reject: '审核拒绝',
      refund: '退款',
      approveOrder: '审核订单',
      ship: '发货',
      shipOrder: '发货',
      refundOrder: '退款',
      confirmRefund: '确认退款',
      reviewFailed: '审核失败',
      procurementFailed: '采购失败',
      shipFailed: '发货失败',
      refundFailed: '退款失败',
      productId: '商品 ID',
      subtotal: '小计',
      addressLine1: '地址行1',
      city: '城市',
      state: '州/省',
      country: '国家',
      phone: '电话',
      reviewedBy: '审核人',
      approved: '是否通过',
      reason: '原因',
      supplier: '供应商',
      supplierId: '供应商 ID',
      supplierSku: '供应商 SKU',
      shipping: '物流信息',
      backToOrders: '返回订单列表',
      orderInfo: '订单信息',
      orderItems: '订单商品',
      procurementInfo: '采购信息',
      pushToProcurement: '推送采购',
      retryProcurement: '重试采购',
      reviewStatus: '审核状态',
      shippingAddress: '收货地址'
    },
    aiProbe: {
      noMessages: '暂无消息',
      aiProbeTitle: 'AI 探测',
      reprobe: '重新探测',
      lastChecked: '上次探测时间',
      overall: '总体状态',
      item: '探测项',
      status: '状态',
      latency: '耗时',
      detail: '详情',
      statusOk: '正常',
      statusWarn: '警告',
      statusFail: '异常',
      aiService: 'AI 服务',
      llmKey: 'LLM API Key',
      database: '数据库'
    },
    users: {
      changeRole: '更改角色',
      selectRole: '选择角色',
      userList: '用户列表',
      noUsers: '暂无用户',
      role: '角色',
      email: '邮箱'
    },
    site: {
      defaultLanguage: '默认语言',
      defaultTheme: '默认主题',
      maintenanceMode: '维护模式',
      openRegistration: '开放注册',
      saveSiteConfig: '保存站点配置',
      siteConfiguration: '站点配置',
      siteName: '站点名称',
      siteSlogan: '站点标语',
      settingsSaveSuccess: '设置保存成功',
      settingsSaveFail: '设置保存失败'
    },
    settings: {
      adminEmail: '管理员邮箱',
      autoReview: '自动审核',
      defaultCurrency: '默认货币',
      emailNotifications: '邮件通知',
      expiryHours: '过期时间（小时）',
      maxItemsPerOrder: '每单最多商品',
      orderAlerts: '订单提醒',
      orderPrefix: '订单前缀',
      orderSettings: '订单设置',
      saveAllSettings: '保存所有设置',
      storeName: '店铺名称',
      storeSettings: '店铺设置'
    },
    login: {
      common: {
        loginOrRegister: '登录 / 注册',
        userNamePlaceholder: '请输入用户名',
        phonePlaceholder: '请输入手机号',
        codePlaceholder: '请输入验证码',
        passwordPlaceholder: '请输入密码',
        confirmPasswordPlaceholder: '请再次输入密码',
        codeLogin: '验证码登录',
        confirm: '确定',
        back: '返回',
        validateSuccess: '验证成功',
        loginSuccess: '登录成功',
        welcomeBack: '欢迎回来，{userName} ！'
      },
      pwdLogin: {
        title: '密码登录',
        rememberMe: '记住我',
        forgetPassword: '忘记密码？',
        register: '注册账号',
        otherAccountLogin: '其他账号登录',
        otherLoginMode: '其他登录方式',
        superAdmin: '超级管理员',
        admin: '管理员',
        user: '普通用户'
      },
      codeLogin: {
        title: '验证码登录',
        getCode: '获取验证码',
        reGetCode: '{time}秒后重新获取',
        sendCodeSuccess: '验证码发送成功',
        imageCodePlaceholder: '请输入图片验证码'
      },
      register: {
        title: '注册账号',
        agreement: '我已经仔细阅读并接受',
        protocol: '《用户协议》',
        policy: '《隐私权政策》'
      },
      resetPwd: {
        title: '重置密码'
      },
      bindWeChat: {
        title: '绑定微信'
      }
    },
    home: {
      branchDesc:
        '为了方便大家开发和更新合并，我们对main分支的代码进行了精简，只保留了首页菜单，其余内容已移至example分支进行维护。预览地址显示的内容即为example分支的内容。',
      greeting: '早安，{userName}, 今天又是充满活力的一天!',
      weatherDesc: '今日多云转晴，20℃ - 25℃!',
      projectCount: '项目数',
      todo: '待办',
      message: '消息',
      downloadCount: '下载量',
      registerCount: '注册量',
      schedule: '作息安排',
      study: '学习',
      work: '工作',
      rest: '休息',
      entertainment: '娱乐',
      visitCount: '访问量',
      turnover: '成交额',
      dealCount: '成交量',
      projectNews: {
        title: '项目动态',
        moreNews: '更多动态',
        desc1: 'Forge 在2021年5月28日创建了开源项目 forge-admin!',
        desc2: 'Yanbowe 向 forge-admin 提交了一个bug，多标签栏不会自适应。',
        desc3: 'Forge 准备为 forge-admin 的发布做充分的准备工作!',
        desc4: 'Forge 正在忙于为forge-admin写项目说明文档！',
        desc5: 'Forge 刚才把工作台页面随便写了一些，凑合能看了！'
      },
      creativity: '创意'
    }
  },
  form: {
    required: '不能为空',
    userName: {
      required: '请输入用户名',
      invalid: '用户名格式不正确'
    },
    phone: {
      required: '请输入手机号',
      invalid: '手机号格式不正确'
    },
    pwd: {
      required: '请输入密码',
      invalid: '密码格式不正确，6-18位字符，包含字母、数字、下划线'
    },
    confirmPwd: {
      required: '请输入确认密码',
      invalid: '两次输入密码不一致'
    },
    code: {
      required: '请输入验证码',
      invalid: '验证码格式不正确'
    },
    email: {
      required: '请输入邮箱',
      invalid: '邮箱格式不正确'
    }
  },
  dropdown: {
    closeCurrent: '关闭',
    closeOther: '关闭其它',
    closeLeft: '关闭左侧',
    closeRight: '关闭右侧',
    closeAll: '关闭所有',
    pin: '固定标签',
    unpin: '取消固定'
  },
  icon: {
    themeConfig: '主题配置',
    themeSchema: '主题模式',
    lang: '切换语言',
    fullscreen: '全屏',
    fullscreenExit: '退出全屏',
    reload: '刷新页面',
    collapse: '折叠菜单',
    expand: '展开菜单',
    pin: '固定',
    unpin: '取消固定'
  },
  datatable: {
    itemCount: '共 {total} 条',
    fixed: {
      left: '左固定',
      right: '右固定',
      unFixed: '取消固定'
    }
  },
  errors: {
    INVALID_CREDENTIALS: '账号或密码不正确',
    UNAUTHORIZED: '请先登录',
    TOKEN_EXPIRED: '登录已过期，请重新登录',
    USER_NOT_FOUND: '用户不存在',
    EMAIL_ALREADY_REGISTERED: '邮箱已被注册'
  }
};

export default local;
