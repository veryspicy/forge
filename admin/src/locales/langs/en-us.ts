const local: App.I18n.Schema = {
  system: {
    title: 'ForgeAdmin',
    updateTitle: 'System Version Update Notification',
    updateContent: 'A new version of the system has been detected. Do you want to refresh the page immediately?',
    updateConfirm: 'Refresh immediately',
    updateCancel: 'Later'
  },
  common: {
    action: 'Action',
    add: 'Add',
    addSuccess: 'Add Success',
    backToHome: 'Back to home',
    batchDelete: 'Batch Delete',
    cancel: 'Cancel',
    close: 'Close',
    check: 'Check',
    selectAll: 'Select All',
    expandColumn: 'Expand Column',
    columnSetting: 'Column Setting',
    config: 'Config',
    confirm: 'Confirm',
    delete: 'Delete',
    deleteSuccess: 'Delete Success',
    confirmDelete: 'Are you sure you want to delete?',
    save: 'Save',
    name: 'Name',
    status: 'Status',
    type: 'Type',
    region: 'Region',
    regions: 'Regions',
    priority: 'Priority',
    active: 'Active',
    inactive: 'Inactive',
    default: 'Default',
    start: 'Start',
    end: 'End',
    calculate: 'Calculate',
    detail: 'Detail',
    view: 'View',
    yes: 'Yes',
    no: 'No',
    adopted: 'Adopted',
    notAdopted: 'Not Adopted',
    conversation: 'Conversation',
    messages: 'Messages',
    userId: 'User ID',
    started: 'Started',
    items: 'Items',
    created: 'Created',
    enforce: 'Enforce',
    language: 'Language',
    regionsComma: 'Regions (comma separated)',
    categoriesComma: 'Categories (comma separated)',
    basicInfo: 'Basic Info',
    tagsRegions: 'Tags & Regions',
    productImages: 'Product Images',
    uploadImages: 'Upload Images',
    dangerZone: 'Danger Zone',
    loadFailed: 'Load failed',
    uploadFailed: 'Upload failed',
    deleteFailed: 'Delete failed',
    saveFailed: 'Save failed',
    quantity: 'Quantity',
    backToList: 'Back to List',
    image: 'Image',
    inventory: 'Inventory',
    cost: 'Cost',
    description: 'Description',
    product: 'Product',
    new: 'New',
    sku: 'SKU',
    origin: 'Origin',
    destination: 'Destination',
    period: 'Period',
    carrier: 'Carrier',
    edit: 'Edit',
    warning: 'Warning',
    error: 'Error',
    index: 'Index',
    keywordSearch: 'Please enter keyword',
    logout: 'Logout',
    logoutConfirm: 'Are you sure you want to log out?',
    lookForward: 'Coming soon',
    modify: 'Modify',
    modifySuccess: 'Modify Success',
    noData: 'No Data',
    publish: 'Publish',
    saveDraft: 'Save Draft',
    operate: 'Operate',
    pleaseCheckValue: 'Please check whether the value is valid',
    refresh: 'Refresh',
    reset: 'Reset',
    search: 'Search',
    switch: 'Switch',
    tip: 'Tip',
    trigger: 'Trigger',
    update: 'Update',
    updateSuccess: 'Update Success',
    userCenter: 'User Center',
    yesOrNo: {
      yes: 'Yes',
      no: 'No'
    }
  },
  request: {
    logout: 'Logout user after request failed',
    logoutMsg: 'User status is invalid, please log in again',
    logoutWithModal: 'Pop up modal after request failed and then log out user',
    logoutWithModalMsg: 'User status is invalid, please log in again',
    refreshToken: 'The requested token has expired, refresh the token',
    tokenExpired: 'The requested token has expired'
  },
  theme: {
    themeDrawerTitle: 'Theme Configuration',
    tabs: {
      appearance: 'Appearance',
      layout: 'Layout',
      general: 'General',
      preset: 'Preset'
    },
    appearance: {
      themeSchema: {
        title: 'Theme Schema',
        light: 'Light',
        dark: 'Dark',
        auto: 'Follow System'
      },
      grayscale: 'Grayscale',
      colourWeakness: 'Colour Weakness',
      themeColor: {
        title: 'Theme Color',
        primary: 'Primary',
        info: 'Info',
        success: 'Success',
        warning: 'Warning',
        error: 'Error',
        followPrimary: 'Follow Primary'
      },
      themeRadius: {
        title: 'Theme Radius'
      },
      recommendColor: 'Apply Recommended Color Algorithm',
      recommendColorDesc: 'The recommended color algorithm refers to',
      preset: {
        title: 'Theme Presets',
        apply: 'Apply',
        applySuccess: 'Preset applied successfully',
        default: {
          name: 'Default Preset',
          desc: 'Default theme preset with balanced settings'
        },
        dark: {
          name: 'Dark Preset',
          desc: 'Dark theme preset for night time usage'
        },
        compact: {
          name: 'Compact Preset',
          desc: 'Compact layout preset for small screens'
        },
        azir: {
          name: "Azir's Preset",
          desc: 'It is a cold and elegant preset that Azir likes'
        }
      }
    },
    layout: {
      layoutMode: {
        title: 'Layout Mode',
        vertical: 'Vertical Mode',
        horizontal: 'Horizontal Mode',
        'vertical-mix': 'Vertical Mix Mode',
        'vertical-hybrid-header-first': 'Left Hybrid Header-First',
        'top-hybrid-sidebar-first': 'Top-Hybrid Sidebar-First',
        'top-hybrid-header-first': 'Top-Hybrid Header-First',
        vertical_detail: 'Vertical menu layout, with the menu on the left and content on the right.',
        'vertical-mix_detail':
          'Vertical mix-menu layout, with the primary menu on the dark left side and the secondary menu on the lighter left side.',
        'vertical-hybrid-header-first_detail':
          'Left hybrid layout, with the primary menu at the top, the secondary menu on the dark left side, and the tertiary menu on the lighter left side.',
        horizontal_detail: 'Horizontal menu layout, with the menu at the top and content below.',
        'top-hybrid-sidebar-first_detail':
          'Top hybrid layout, with the primary menu on the left and the secondary menu at the top.',
        'top-hybrid-header-first_detail':
          'Top hybrid layout, with the primary menu at the top and the secondary menu on the left.'
      },
      tab: {
        title: 'Tab Settings',
        visible: 'Tab Visible',
        cache: 'Tag Bar Info Cache',
        cacheTip: 'Keep the tab bar information after leaving the page',
        height: 'Tab Height',
        mode: {
          title: 'Tab Mode',
          slider: 'Slider',
          chrome: 'Chrome',
          button: 'Button'
        },
        closeByMiddleClick: 'Close Tab by Middle Click',
        closeByMiddleClickTip: 'Enable closing tabs by clicking with the middle mouse button'
      },
      header: {
        title: 'Header Settings',
        height: 'Header Height',
        breadcrumb: {
          visible: 'Breadcrumb Visible',
          showIcon: 'Breadcrumb Icon Visible'
        }
      },
      sider: {
        title: 'Sider Settings',
        inverted: 'Dark Sider',
        width: 'Sider Width',
        collapsedWidth: 'Sider Collapsed Width',
        mixWidth: 'Mix Sider Width',
        mixCollapsedWidth: 'Mix Sider Collapse Width',
        mixChildMenuWidth: 'Mix Child Menu Width',
        autoSelectFirstMenu: 'Auto Select First Submenu',
        autoSelectFirstMenuTip:
          'When a first-level menu is clicked, the first submenu is automatically selected and navigated to the deepest level'
      },
      footer: {
        title: 'Footer Settings',
        visible: 'Footer Visible',
        fixed: 'Fixed Footer',
        height: 'Footer Height',
        right: 'Right Footer'
      },
      content: {
        title: 'Content Area Settings',
        scrollMode: {
          title: 'Scroll Mode',
          tip: 'The theme scroll only scrolls the main part, the outer scroll can carry the header and footer together',
          wrapper: 'Wrapper',
          content: 'Content'
        },
        page: {
          animate: 'Page Animate',
          mode: {
            title: 'Page Animate Mode',
            fade: 'Fade',
            'fade-slide': 'Slide',
            'fade-bottom': 'Fade Zoom',
            'fade-scale': 'Fade Scale',
            'zoom-fade': 'Zoom Fade',
            'zoom-out': 'Zoom Out',
            none: 'None'
          }
        },
        fixedHeaderAndTab: 'Fixed Header And Tab'
      }
    },
    general: {
      title: 'General Settings',
      watermark: {
        title: 'Watermark Settings',
        visible: 'Watermark Full Screen Visible',
        text: 'Custom Watermark Text',
        enableUserName: 'Enable User Name Watermark',
        enableTime: 'Show Current Time',
        timeFormat: 'Time Format'
      },
      multilingual: {
        title: 'Multilingual Settings',
        visible: 'Display multilingual button'
      },
      globalSearch: {
        title: 'Global Search Settings',
        visible: 'Display GlobalSearch button'
      }
    },
    configOperation: {
      copyConfig: 'Copy Config',
      copySuccessMsg: 'Copy Success, Please replace the variable "themeSettings" in "src/theme/settings.ts"',
      resetConfig: 'Reset Config',
      resetSuccessMsg: 'Reset Success'
    }
  },
  route: {
    login: 'Login',
    403: 'No Permission',
    404: 'Page Not Found',
    500: 'Server Error',
    'iframe-page': 'Iframe',
    dashboard: 'Dashboard',
    resources: 'Resources',
    suppliers: 'Suppliers',
    pricing: 'Pricing',
    shipments: 'Shipments',
    products: 'Products',
    'products-new': 'New Product',
    'products-detail': 'Edit Product',
    orders: 'Orders',
    'orders-detail': 'Order Detail',
    'ai-probe': 'AI Probe',
    users: 'Users',
    settings: 'Settings',
    'admin-users': 'Admin Users',
    roles: 'Roles',
    'site-config': 'Site Config'
  },
  page: {
    dashboard: {
      todayOrders: 'Today Orders',
      pendingOrders: 'Pending Orders',
      todayGMV: 'Today GMV',
      activeProducts: 'Active Products',
      probeAdoption: 'Probe Adoption',
      procurementErrors: 'Procurement Errors',
      activeSuppliers: 'Active Suppliers',
      probeRequests: 'Probe Requests',
      ordersTrend: 'Orders Trend (7 days)',
      productCategories: 'Product Categories'
    },
    suppliers: {
      contactEmail: 'Contact Email',
      contactPhone: 'Contact Phone',
      defaultCurrency: 'Default Currency',
      integrationType: 'Integration Type',
      shippingRegions: 'Shipping Regions',
      supplierList: 'Supplier List',
      addSupplier: 'Add Supplier',
      editSupplier: 'Edit Supplier',
      name: 'Name',
      status: 'Status',
      actions: 'Actions',
      active: 'Active',
      inactive: 'Inactive',
      address: 'Address',
      noSupplier: 'No suppliers yet',
      provider: 'Provider',
      providerCode: 'Provider Code',
      providerCodePlaceholder: 'Select source provider (new only)',
      credentials: 'Credentials',
      accessToken: 'Access Token',
      tokenType: 'Token Type',
      saveCredentials: 'Save Credentials',
      credSaved: 'Credentials saved',
      credentialsMissing: 'No credentials',
      searchProducts: 'Search Products',
      searchKeyword: 'Keyword',
      searchPlaceholder: 'Type keyword to search products',
      search: 'Search',
      importSelected: 'Import Selected',
      noSearchResult: 'No products found',
      price: 'Price',
      inventory: 'Inventory',
      imported: 'Imported',
      failed: 'Failed',
      syncNow: 'Sync Now',
      syncLogs: 'Sync Logs',
      syncStatus: 'Sync Status',
      triggerType: 'Trigger',
      itemsTotal: 'Items',
      itemsImported: 'Imported',
      itemsUpdated: 'Updated',
      startedAt: 'Started At',
      finishedAt: 'Finished At',
      noLogs: 'No sync logs',
      syncing: 'Syncing...',
      syncDone: 'Sync completed',
      syncFailed: 'Sync failed',
      manual: 'Manual',
      scheduled: 'Scheduled',
      success: 'Success',
      running: 'Running',
      partial: 'Partial',
      confirmImport: 'Import selected products?',
      importResult: 'Import done: {imported} imported, {failed} failed'
    },
    pricing: {
      title: 'Pricing',
      costPrice: 'Cost Price',
      fixedShippingFee: 'Fixed Shipping Fee',
      markupMultiplier: 'Markup Multiplier',
      overridePrice: 'Override Price (optional)',
      priceCalculator: 'Price Calculator',
      pricingRule: 'Pricing Rule',
      productId: 'Product ID (optional)',
      addRule: 'Add Rule',
      noRules: 'No pricing rules yet',
      promotions: 'Promotions',
      noPromotions: 'No promotions yet',
      promoCount: '{count} promotion(s)',
      coupon: 'Coupon',
      discount: 'Discount',
      bundle: 'Bundle'
    },
    shipments: {
      estimatedDelivery: 'Estimated Delivery',
      orderId: 'Order ID',
      trackingNumber: 'Tracking Number',
      shipmentList: 'Shipment List',
      noShipments: 'No shipments yet',
      carrier: 'Carrier',
      newShipment: 'New Shipment',
      editShipment: 'Edit Shipment',
      eta: 'ETA'
    },
    products: {
      allCategories: 'All Categories',
      productList: 'Product List',
      noProducts: 'No products yet',
      category: 'Category',
      price: 'Price',
      export: 'Export',
      import: 'Import',
      importResult: 'Import Result',
      importCreated: 'Created',
      importUpdated: 'Updated',
      importFailed: 'Failed',
      importRow: 'Row',
      importError: 'Error'
    },
    productsDetail: {
      aiGenerated: 'AI Generated',
      backToList: 'Back to List',
      basicInfo: 'Basic Info',
      changeStatus: 'Change status',
      costUsd: 'Cost (USD)',
      dangerZone: 'Danger Zone',
      priceUsd: 'Price (USD)',
      productImages: 'Product Images',
      regionsComma: 'Regions (comma separated)',
      saveProduct: 'Save Product',
      tagsComma: 'Tags (comma separated)',
      updateStatus: 'Update Status',
      uploadImages: 'Upload Images',
      editProduct: 'Edit Product',
      slug: 'Slug',
      inventory: 'Inventory',
      sku: 'SKU',
      statusUpdateFailed: 'Status update failed'
    },
    orders: {
      allStatus: 'All Status',
      orderList: 'Order List',
      noOrders: 'No orders yet',
      orderNumber: 'Order Number',
      total: 'Total',
      date: 'Date'
    },
    ordersDetail: {
      backToOrders: 'Back to Orders',
      orderInfo: 'Order Info',
      orderItems: 'Order Items',
      procurementInfo: 'Procurement Info',
      pushToProcurement: 'Push to Procurement',
      retryProcurement: 'Retry Procurement',
      reviewStatus: 'Review Status',
      shippingAddress: 'Shipping Address',
      approve: 'Approve',
      reject: 'Reject',
      refund: 'Refund',
      ship: 'Ship',
      shipping: 'Shipping',
      supplier: 'Supplier',
      supplierId: 'Supplier ID',
      supplierSku: 'Supplier SKU',
      approved: 'Approved',
      reason: 'Reason',
      reviewedBy: 'Reviewed By',
      city: 'City',
      state: 'State',
      country: 'Country',
      phone: 'Phone',
      addressLine1: 'Line 1',
      productId: 'Product ID',
      subtotal: 'Subtotal',
      approveOrder: 'Approve Order',
      refundOrder: 'Refund Order',
      shipOrder: 'Ship Order',
      reviewFailed: 'Review failed',
      procurementFailed: 'Procurement failed',
      shipFailed: 'Ship failed',
      refundFailed: 'Refund failed',
      confirmRefund: 'Confirm Refund'
    },
    aiProbe: {
      noMessages: 'No messages',
      aiProbeTitle: 'AI Probe',
      reprobe: 'Re-probe',
      lastChecked: 'Last checked',
      overall: 'Overall',
      item: 'Item',
      status: 'Status',
      latency: 'Latency',
      detail: 'Detail',
      statusOk: 'OK',
      statusWarn: 'Warning',
      statusFail: 'Failed',
      aiService: 'AI Service',
      llmKey: 'LLM API Key',
      database: 'Database'
    },
    users: {
      changeRole: 'Change Role',
      selectRole: 'Select role',
      userList: 'User List',
      noUsers: 'No users yet',
      role: 'Role',
      email: 'Email'
    },
    site: {
      defaultLanguage: 'Default Language',
      defaultTheme: 'Default Theme',
      maintenanceMode: 'Maintenance Mode',
      openRegistration: 'Open Registration',
      saveSiteConfig: 'Save Site Config',
      siteConfiguration: 'Site Configuration',
      siteName: 'Site Name',
      siteSlogan: 'Site Slogan',
      settingsSaveSuccess: 'Settings saved successfully',
      settingsSaveFail: 'Failed to save settings'
    },
    settings: {
      adminEmail: 'Admin Email',
      autoReview: 'Auto Review',
      defaultCurrency: 'Default Currency',
      emailNotifications: 'Email Notifications',
      expiryHours: 'Expiry (hours)',
      maxItemsPerOrder: 'Max Items Per Order',
      orderAlerts: 'Order Alerts',
      orderPrefix: 'Order Prefix',
      orderSettings: 'Order Settings',
      saveAllSettings: 'Save All Settings',
      storeName: 'Store Name',
      storeSettings: 'Store Settings'
    },
    login: {
      common: {
        loginOrRegister: 'Login / Register',
        userNamePlaceholder: 'Please enter user name',
        phonePlaceholder: 'Please enter phone number',
        codePlaceholder: 'Please enter verification code',
        passwordPlaceholder: 'Please enter password',
        confirmPasswordPlaceholder: 'Please enter password again',
        codeLogin: 'Verification code login',
        confirm: 'Confirm',
        back: 'Back',
        validateSuccess: 'Verification passed',
        loginSuccess: 'Login successfully',
        welcomeBack: 'Welcome back, {userName} !'
      },
      pwdLogin: {
        title: 'Password Login',
        rememberMe: 'Remember me',
        forgetPassword: 'Forget password?',
        register: 'Register',
        otherAccountLogin: 'Other Account Login',
        otherLoginMode: 'Other Login Mode',
        superAdmin: 'Super Admin',
        admin: 'Admin',
        user: 'User'
      },
      codeLogin: {
        title: 'Verification Code Login',
        getCode: 'Get verification code',
        reGetCode: 'Reacquire after {time}s',
        sendCodeSuccess: 'Verification code sent successfully',
        imageCodePlaceholder: 'Please enter image verification code'
      },
      register: {
        title: 'Register',
        agreement: 'I have read and agree to',
        protocol: '《User Agreement》',
        policy: '《Privacy Policy》'
      },
      resetPwd: {
        title: 'Reset Password'
      },
      bindWeChat: {
        title: 'Bind WeChat'
      }
    },
    home: {
      branchDesc:
        'For the convenience of everyone in developing and updating the merge, we have streamlined the code of the main branch, only retaining the homepage menu, and the rest of the content has been moved to the example branch for maintenance. The preview address displays the content of the example branch.',
      greeting: 'Good morning, {userName}, today is another day full of vitality!',
      weatherDesc: 'Today is cloudy to clear, 20℃ - 25℃!',
      projectCount: 'Project Count',
      todo: 'Todo',
      message: 'Message',
      downloadCount: 'Download Count',
      registerCount: 'Register Count',
      schedule: 'Work and rest Schedule',
      study: 'Study',
      work: 'Work',
      rest: 'Rest',
      entertainment: 'Entertainment',
      visitCount: 'Visit Count',
      turnover: 'Turnover',
      dealCount: 'Deal Count',
      projectNews: {
        title: 'Project News',
        moreNews: 'More News',
        desc1: 'Forge created the open source project forge-admin on May 28, 2021!',
        desc2: 'Yanbowe submitted a bug to forge-admin, the multi-tab bar will not adapt.',
        desc3: 'Forge is ready to do sufficient preparation for the release of forge-admin!',
        desc4: 'Forge is busy writing project documentation for forge-admin!',
        desc5: 'Forge just wrote some of the workbench pages casually, and it was enough to see!'
      },
      creativity: 'Creativity'
    }
  },
  form: {
    required: 'Cannot be empty',
    userName: {
      required: 'Please enter user name',
      invalid: 'User name format is incorrect'
    },
    phone: {
      required: 'Please enter phone number',
      invalid: 'Phone number format is incorrect'
    },
    pwd: {
      required: 'Please enter password',
      invalid: '6-18 characters, including letters, numbers, and underscores'
    },
    confirmPwd: {
      required: 'Please enter password again',
      invalid: 'The two passwords are inconsistent'
    },
    code: {
      required: 'Please enter verification code',
      invalid: 'Verification code format is incorrect'
    },
    email: {
      required: 'Please enter email',
      invalid: 'Email format is incorrect'
    }
  },
  dropdown: {
    closeCurrent: 'Close Current',
    closeOther: 'Close Other',
    closeLeft: 'Close Left',
    closeRight: 'Close Right',
    closeAll: 'Close All',
    pin: 'Pin Tab',
    unpin: 'Unpin Tab'
  },
  icon: {
    themeConfig: 'Theme Configuration',
    themeSchema: 'Theme Schema',
    lang: 'Switch Language',
    fullscreen: 'Fullscreen',
    fullscreenExit: 'Exit Fullscreen',
    reload: 'Reload Page',
    collapse: 'Collapse Menu',
    expand: 'Expand Menu',
    pin: 'Pin',
    unpin: 'Unpin'
  },
  datatable: {
    itemCount: 'Total {total} items',
    fixed: {
      left: 'Left Fixed',
      right: 'Right Fixed',
      unFixed: 'Unfixed'
    }
  },
  errors: {
    INVALID_CREDENTIALS: 'Invalid email or password',
    UNAUTHORIZED: 'Please log in first',
    TOKEN_EXPIRED: 'Session expired, please log in again',
    USER_NOT_FOUND: 'User not found',
    EMAIL_ALREADY_REGISTERED: 'Email already registered'
  }
};

export default local;
